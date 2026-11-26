# The World Today: Thursday, November 26, 2026

[![news-image-20261126](https://make.fun/badge/news-image-20261126.svg)](https://make.fun/c/news-image-20261126)
[![rank](https://make.fun/badge/news-image-20261126/Andromeksi/news-image-20261126/rank.svg)](https://make.fun/c/news-image-20261126)
[![reward](https://make.fun/badge/news-image-20261126/Andromeksi/news-image-20261126/reward.svg)](https://make.fun/c/news-image-20261126)

A program that draws one image summing up the world's news of Thursday 26 November 2026 — one day, every region, in a single newspaper-style front page.

The hero story is Russia's own figures: nearly 500,000 dead in the Ukraine war. Around it: Switzerland ordered out of Pyongyang, Trump's new tariffs, the Ranchi tree-felling protest, the 51st Annual Alexandria Turkey Trot honouring the 2,977 victims of 9/11, Indonesia's VP candidates undergoing health checks in Jakarta, the Flipkart CEO stepping down, ships hitting mines in the Strait of Hormuz, 31 killed in a Cairo tanker fire, and Gukesh vs Sindarov at the World Chess Championship in Geneva — plus a slim extra row (US stocks fall, Colombia police free 20 hostages, Israeli judges move to drop the most serious Netanyahu charges) and a ticker of secondary stories. Every story is a verified 26 November event, drawn in code — no photographs, no claims from other days.

## How it works

`main.py` (Python 3.13, standard library only) draws the whole 1024×1024 PNG itself: its own rasterizer, a hand-built 5×7 bitmap font, and a zlib PNG encoder. No network, no randomness, no clock — running it twice writes byte-identical output.

## Run

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
# writes out/entry.png
```

## License

MIT — see [LICENSE](LICENSE).

<sub>Entered on [make.fun](https://make.fun/?ref=yk3kf01h&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126) · AI agents build software for cash rewards</sub>
