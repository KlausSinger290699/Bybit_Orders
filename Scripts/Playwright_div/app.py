# app.py
import argparse
import asyncio
from core import StrategyEngine
from adapters import ConsolePrinter, RandomDemoSource, NDJSONReplaySource, PlaywrightSource

async def run(source, sink):
    engine = StrategyEngine(sink=sink)
    async for ev in source.events():
        engine.on_event(ev)
    if hasattr(sink, "flush_now"):
        sink.flush_now()

def parse_args():
    ap = argparse.ArgumentParser(description="CVD bot (clean 3-file split)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="Run random demo (no browser) [default]")
    mode.add_argument("--replay", type=str, help="Replay NDJSON file (no browser)")
    mode.add_argument("--live", action="store_true", help="Playwright live mode (browser)")
    ap.add_argument("--tf", type=int, default=900, help="Timeframe seconds for demo (default 900=15m)")
    ap.add_argument("--count", type=int, default=30, help="Number of demo events")
    ap.add_argument("--match", type=float, default=0.30, help="Probability to force L2(prev)==L1(next❔)")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for demo")
    ap.add_argument("--url", default="https://charts.aggr.trade/koenzv4")
    ap.add_argument("--profile", default=r"C:\Users\Anwender\PlaywrightProfiles\aggr")
    return ap.parse_args()

async def main():
    args = parse_args()
    sink = ConsolePrinter()

    if args.replay:
        src = NDJSONReplaySource(args.replay)
    elif args.live:
        src = PlaywrightSource(url=args.url, profile_dir=args.profile)
    else:
        # default to demo unless replay/live explicitly chosen
        src = RandomDemoSource(
            tf_sec=args.tf,
            n_events=args.count,
            match_prob=args.match,
            seed=args.seed
        )

    await run(src, sink)

if __name__ == "__main__":
    asyncio.run(main())
