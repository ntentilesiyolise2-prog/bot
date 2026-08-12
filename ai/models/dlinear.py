import torch
import torch.nn as nn
import numpy as np

class DLinear(nn.Module):
    def __init__(self, seq_len=60, pred_len=5, enc_in=1, individual=False):
        super(DLinear, self).__init__()
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.individual = individual
        
        if self.individual:
            self.Linear_Seasonal = nn.ModuleList()
            self.Linear_Trend = nn.ModuleList()
            for i in range(enc_in):
                self.Linear_Seasonal.append(nn.Linear(seq_len, pred_len))
                self.Linear_Trend.append(nn.Linear(seq_len, pred_len))
        else:
            self.Linear_Seasonal = nn.Linear(seq_len, pred_len)
            self.Linear_Trend = nn.Linear(seq_len, pred_len)

    def forward(self, x):
        # x: [Batch, Input length, Features]
        # Decompose by moving average
        moving_avg = torch.avg_pool1d(x.permute(0,2,1), kernel_size=3, stride=1, padding=1).permute(0,2,1)
        trend = moving_avg
        seasonal = x - trend
        
        if self.individual:
            seasonal_output = torch.stack([self.Linear_Seasonal[i](seasonal[:, :, i]) for i in range(x.shape[-1])], dim=-1)
            trend_output = torch.stack([self.Linear_Trend[i](trend[:, :, i]) for i in range(x.shape[-1])], dim=-1)
        else:
            seasonal_output = self.Linear_Seasonal(seasonal.permute(0,2,1)).permute(0,2,1)
            trend_output = self.Linear_Trend(trend.permute(0,2,1)).permute(0,2,1)
        
        return seasonal_output + trend_output
