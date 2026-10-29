"""Step 3 – multi-task GRU and LSTM (PyTorch, GPU if available).

Early stopping on the mean validation PR-AUC of the nine tasks; per-task calibration and
CSI-optimal thresholds on validation. Predictions are merged into
results/predictions/pred_<target>_<h>h.parquet as columns 'gru'/'lstm' (+ '_raw').
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.config import MODELS, RANDOM_STATE, RESULTS  # noqa: E402
from esenboga.data import fog_season, load_processed, split_labels  # noqa: E402
from esenboga.deep import (SEQ_LEN, TASKS, SeqNet, build_arrays, gather_windows,  # noqa: E402
                           predict_logits)
from esenboga.models import choose_calibrator  # noqa: E402
from esenboga.metrics import best_threshold  # noqa: E402

PRED_DIR = RESULTS / "predictions"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


SEARCH = [  # (hidden, dropout, learning rate, weight decay)
    (64, 0.2, 1e-3, 1e-4), (128, 0.3, 5e-4, 1e-4), (32, 0.2, 1e-3, 1e-4),
    (64, 0.4, 5e-4, 1e-3), (128, 0.4, 3e-4, 1e-3), (64, 0.3, 3e-4, 1e-4),
]


def train_one(cell: str, S, Z, Y, idx_tr, idx_va, device, epochs=30, patience=5,
              batch=1024, lr=1e-3, hidden=64, dropout=0.2, wd=1e-4, seed=RANDOM_STATE,
              verbose=True):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = SeqNet(S.shape[1], Z.shape[1], len(TASKS), cell=cell, hidden=hidden,
                   dropout=dropout).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=2)
    Yt = torch.as_tensor(np.nan_to_num(Y, nan=-1.0), device=device)
    pos = np.nanmean(Y[idx_tr], axis=0)
    pos_weight = torch.as_tensor(np.sqrt((1 - pos) / np.maximum(pos, 1e-4)), device=device)
    bce = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight, reduction="none")
    best, best_state, bad = -1.0, None, 0
    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(idx_tr)
        tot = 0.0
        for k in range(0, len(perm), batch):
            b = torch.as_tensor(perm[k:k + batch], device=device)
            logits = model(gather_windows(S, b), Z[b])
            yb = Yt[b]
            mask = (yb >= 0).float()
            loss = (bce(logits, yb.clamp(min=0)) * mask).sum() / mask.sum().clamp(min=1)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot += loss.item() * len(b)
        lv = predict_logits(model, S, Z, idx_va)
        aps = []
        for j in range(len(TASKS)):
            yv = Y[idx_va, j]
            ok = ~np.isnan(yv)
            if yv[ok].sum() > 0:
                aps.append(average_precision_score(yv[ok], lv[ok, j]))
        score = float(np.mean(aps))
        sched.step(score)
        if verbose:
            log(f"  {cell} epoch {ep + 1:02d} loss={tot / len(perm):.4f} val meanAP={score:.4f}")
        if score > best + 1e-4:
            best, bad = score, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    return model, best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", nargs="+", default=["gru", "lstm"])
    ap.add_argument("--epochs", type=int, default=30)
    args = ap.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    feats, targ = load_processed()
    split = split_labels(feats.index).to_numpy()
    tr_mask = split == "train"
    # normalisation statistics from the training period only
    _, _, _, stats = build_arrays(feats[tr_mask], targ[tr_mask])
    S_np, Z_np, Y, _ = build_arrays(feats, targ, stats)
    present = feats["vis_m"].notna().to_numpy()
    has_y = ~np.all(np.isnan(Y), axis=1)
    pos = np.arange(len(feats))
    usable = present & has_y & (pos >= SEQ_LEN - 1)
    idx_tr = pos[usable & (split == "train")]
    idx_va = pos[usable & (split == "val")]
    S = torch.as_tensor(S_np, device=device)
    Z = torch.as_tensor(Z_np, device=device)
    log(f"device={device} train={len(idx_tr):,} val={len(idx_va):,} seq_vars={S.shape[1]}")
    idx_all = pos[present & (pos >= SEQ_LEN - 1)]

    for cell in args.cells:
        t0 = time.time()
        results = []
        for hidden, dropout, lr, wd in SEARCH:
            m_, s_ = train_one(cell, S, Z, Y, idx_tr, idx_va, device, epochs=args.epochs,
                               lr=lr, hidden=hidden, dropout=dropout, wd=wd, verbose=False)
            results.append((s_, (hidden, dropout, lr, wd), m_))
            log(f"  {cell} hidden={hidden} dropout={dropout} lr={lr} wd={wd}: val meanAP={s_:.4f}")
        best, cfg, model = max(results, key=lambda r: r[0])
        log(f"  {cell} selected {cfg}")
        logits = predict_logits(model, S, Z, idx_all)
        probs = 1 / (1 + np.exp(-logits))
        bundle = {"state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                  "cell": cell, "stats": stats, "n_seq": S.shape[1], "n_static": Z.shape[1],
                  "config": dict(zip(("hidden", "dropout", "lr", "weight_decay"), cfg)),
                  "search": [(s, c) for s, c, _ in results],
                  "calibrators": {}, "thresholds": {}}
        val_pos = np.isin(idx_all, idx_va)
        seasons = fog_season(feats.index[idx_all[val_pos]])
        out = pd.DataFrame(index=feats.index[idx_all])
        for j, (t, h) in enumerate(TASKS):
            yv = Y[idx_all[val_pos], j]
            ok = ~np.isnan(yv)
            cal, _ = choose_calibrator(probs[val_pos, j][ok], yv[ok].astype(int), seasons[ok])
            thr = best_threshold(yv[ok], cal.transform(probs[val_pos, j][ok]), "CSI")
            bundle["calibrators"][f"{t}_{h}h"] = cal
            bundle["thresholds"][f"{t}_{h}h"] = thr
            out[f"{t}_{h}h_raw"] = probs[:, j]
            out[f"{t}_{h}h"] = cal.transform(probs[:, j])
        PRED_DIR.mkdir(parents=True, exist_ok=True)
        out.to_parquet(PRED_DIR / f"deep_{cell}.parquet")
        joblib.dump(bundle, MODELS / f"deep_{cell}.joblib")
        log(f"{cell}: best val meanAP={best:.4f} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
