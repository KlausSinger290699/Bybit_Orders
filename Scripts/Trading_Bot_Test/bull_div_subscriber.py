# bull_div_subscriber.py
import bull_div_reader_sync

# simple counters to verify we get everything
count = {"n": 0}

@bull_div_reader_sync.bus.on("divergence")
def handle_divergence(data):
    count["n"] += 1
    # Print a compact sanity line
    print(
        f"📩 Received #{count['n']} | "
        f"L1={data['L1']} T1={data['T1']} | "
        f"L2={data['L2']} T2={data['T2']} | "
        f"L3={data['L3']} T3={data['T3']} | "
        f"L4={data['L4']} T4={data['T4']} | "
        f"SL={data['SL']} | Tradable={data['Tradable']}"
    )

if __name__ == "__main__":
    bull_div_reader_sync.main()
