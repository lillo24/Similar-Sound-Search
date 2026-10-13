"""Inference-only MN04 adaptation of EfficientAT a425fdc, MIT (see LICENSE-EfficientAT.md).

Copyright (c) 2022 Florian Schmid. Only the default channel-SE/MLP architecture is
retained. No training, URL loader, fallback state loading or automatic downloads.
"""

import torch
from torch import nn


def divisible(value):
    result = max(8, int(value + 4) // 8 * 8)
    return result + 8 if result < 0.9 * value else result


def conv(inc, out, kernel=1, stride=1, groups=1, activation=nn.Hardswish):
    layers = [
        nn.Conv2d(inc, out, kernel, stride, (kernel - 1) // 2, groups=groups, bias=False),
        nn.BatchNorm2d(out, eps=0.001, momentum=0.01),
    ]
    if activation:
        layers.append(activation(inplace=True))
    return nn.Sequential(*layers)


class SqueezeExcitation(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.fc1 = nn.Linear(channels, divisible(channels // 4))
        self.fc2 = nn.Linear(divisible(channels // 4), channels)

    def forward(self, x):
        scale = x.mean((2, 3))
        scale = torch.sigmoid(self.fc2(torch.relu(self.fc1(scale))))
        return x * scale[:, :, None, None]


class ConcurrentSE(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conc_se_layers = nn.ModuleList([SqueezeExcitation(channels)])

    def forward(self, x):
        return self.conc_se_layers[0](x)


class Block(nn.Module):
    def __init__(self, inc, expanded, out, kernel, stride, se, hs):
        super().__init__()
        activation = nn.Hardswish if hs else nn.ReLU
        layers = []
        if expanded != inc:
            layers.append(conv(inc, expanded, activation=activation))
        layers.append(conv(expanded, expanded, kernel, stride, expanded, activation))
        if se:
            layers.append(ConcurrentSE(expanded))
        layers.append(conv(expanded, out, activation=None))
        self.block = nn.Sequential(*layers)
        self.residual = inc == out and stride == 1

    def forward(self, x):
        y = self.block(x)
        return y + x if self.residual else y


class MN04(nn.Module):
    def __init__(self):
        super().__init__()
        # inc, expansion, out, kernel, stride, channel-SE, hard-swish; width .4.
        settings = [
            (16, 16, 16, 3, 1, False, False),
            (16, 64, 24, 3, 2, False, False),
            (24, 72, 24, 3, 1, False, False),
            (24, 72, 40, 5, 2, True, False),
            (40, 120, 40, 5, 1, True, False),
            (40, 120, 40, 5, 1, True, False),
            (40, 240, 80, 3, 2, False, True),
            (80, 200, 80, 3, 1, False, True),
            (80, 184, 80, 3, 1, False, True),
            (80, 184, 80, 3, 1, False, True),
            (80, 480, 112, 3, 1, True, True),
            (112, 672, 112, 3, 1, True, True),
            (112, 672, 160, 5, 2, True, True),
            (160, 960, 160, 5, 1, True, True),
            (160, 960, 160, 5, 1, True, True),
        ]
        layers = [conv(1, divisible(16 * 0.4), 3, 2)]
        for inc, expanded, out, kernel, stride, se, hs in settings:
            layers.append(
                Block(
                    divisible(inc * 0.4),
                    divisible(expanded * 0.4),
                    divisible(out * 0.4),
                    kernel,
                    stride,
                    se,
                    hs,
                )
            )
        layers.append(conv(divisible(160 * 0.4), 6 * divisible(160 * 0.4)))
        self.features = nn.Sequential(*layers)
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(1),
            nn.Linear(384, divisible(1280 * 0.4)),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.2, inplace=True),
            nn.Linear(divisible(1280 * 0.4), 527),
        )

    def forward(self, x):
        # Same returned retrieval embedding as upstream: mean of last convolution,
        # before the classifier; no logits or separated stems are returned.
        return self.features(x).mean((2, 3))
