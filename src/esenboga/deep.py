"""Multi-task recurrent networks (GRU / LSTM) for low-visibility nowcasting.

One network reads the last ``SEQ_LEN`` half-hourly grid states (12 h) and predicts all nine
binary tasks {VIS<1000 m, RVR<550 m, RVR<350 m} x {1, 3, 6 h} with a masked binary
cross-entropy. Long-memory and valid-time astronomical features enter as static inputs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch import nn

from .features import valid_time_features

SEQ_LEN = 24
SEQ_VARS = ["log_vis", "rvr_eff_m", "temp_c", "dewpt_c", "dpd_c", "rh_pct", "wind_u", "wind_v",
            "wind_speed_kt", "qnh_hpa", "log_ceiling_ft", "log_lowest_cloud_ft",
            "max_cover_octas", "fog_now", "wx_fg", "wx_shallow_fg", "wx_br", "wx_precip",
            "wx_sn", "solar_elev", "hour_sin", "hour_cos"]
STATIC_VARS = ["doy_sin", "doy_cos", "h_since_fog", "fog_frac_24h", "snow_frac_72h",
               "precip_frac_12h", "T_minus_max12h"]
TASKS = [(t, h) for h in (1, 3, 6) for t in ("fog", "rvr550", "rvr350")]


def build_arrays(feats: pd.DataFrame, targ: pd.DataFrame, stats: dict | None = None):
    """Normalised sequence matrix (T x F+1), static matrix and target matrix on the grid."""
    seq = feats[SEQ_VARS].copy()
    seq["rvr_eff_m"] = np.log10(seq["rvr_eff_m"].clip(lower=25))
    present = feats["vis_m"].notna().astype(np.float32)
    static = feats[STATIC_VARS].copy()
    for h in (1, 3, 6):
        vt = valid_time_features(feats.index, h)
        static[f"vt_solar_elev_{h}"] = vt["vt_solar_elev"]
        static[f"vt_h_to_sunrise_{h}"] = vt["vt_h_to_sunrise"]
    if stats is None:
        stats = {"seq_mu": seq.mean(), "seq_sd": seq.std().replace(0, 1),
                 "st_mu": static.mean(), "st_sd": static.std().replace(0, 1)}
    seq = ((seq.ffill(limit=2) - stats["seq_mu"]) / stats["seq_sd"]).fillna(0.0)
    static = ((static - stats["st_mu"]) / stats["st_sd"]).fillna(0.0)
    S = np.column_stack([seq.to_numpy(np.float32), present.to_numpy()[:, None]])
    Z = static.to_numpy(np.float32)
    Y = None
    if targ is not None:
        cols = []
        for t, h in TASKS:
            r = targ[f"y_rvr_{h}h"]
            if t == "fog":
                cols.append(targ[f"y_fog_{h}h"])
            elif t == "rvr550":
                cols.append((r >= 1).astype(float).where(r.notna()))
            else:
                cols.append((r >= 2).astype(float).where(r.notna()))
        Y = np.column_stack([c.to_numpy(np.float32) for c in cols])
    return S, Z, Y, stats


class SeqNet(nn.Module):
    def __init__(self, n_seq: int, n_static: int, n_out: int, cell: str = "gru",
                 hidden: int = 64, layers: int = 2, dropout: float = 0.2):
        super().__init__()
        rnn = nn.GRU if cell == "gru" else nn.LSTM
        self.rnn = rnn(n_seq, hidden, num_layers=layers, batch_first=True, dropout=dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden + n_static, 128), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, n_out))

    def forward(self, x_seq, x_static):
        out, _ = self.rnn(x_seq)
        return self.head(torch.cat([out[:, -1], x_static], dim=1))


def gather_windows(S: torch.Tensor, idx: torch.Tensor, seq_len: int = SEQ_LEN) -> torch.Tensor:
    offs = torch.arange(-seq_len + 1, 1, device=S.device)
    return S[(idx[:, None] + offs[None, :]).clamp(min=0)]


@torch.no_grad()
def predict_logits(model: SeqNet, S: torch.Tensor, Z: torch.Tensor, idx: np.ndarray,
                   batch: int = 4096) -> np.ndarray:
    model.eval()
    out = []
    for k in range(0, len(idx), batch):
        b = torch.as_tensor(idx[k:k + batch], device=S.device)
        out.append(model(gather_windows(S, b), Z[b]).float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, len(TASKS)), np.float32)
