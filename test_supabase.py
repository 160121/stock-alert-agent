import json
from app.services.supabase_client import supabase  # Your Supabase client

def debug_symbols_from_supabase():
    try:
        response = supabase.table("subscriptions").select("*").execute()
        if not hasattr(response, "data") or response.data is None:
            print("No data received from Supabase")
            return

        subscriptions = response.data
        for sub in subscriptions:
            print(f"Raw symbols from Supabase for chat_id={sub['chat_id']}: {sub['symbols']} (type: {type(sub['symbols'])})")
            try:
                symbols_list = json.loads(sub["symbols"])
                print(f"Parsed symbols (list) for chat_id={sub['chat_id']}: {symbols_list} (type: {type(symbols_list)})")
            except Exception as e:
                print(f"Failed to parse symbols for chat_id={sub['chat_id']}: {e}")

    except Exception as e:
        print(f"Error fetching from Supabase: {e}")

def debug_symbols_input(symbols):
    print(f"Symbols received as input: {symbols} (type: {type(symbols)})")
    if isinstance(symbols, str):
        try:
            parsed = json.loads(symbols)
            print(f"Parsed symbols from input string: {parsed} (type: {type(parsed)})")
        except Exception as e:
            print(f"Failed to parse input symbols string: {e}")

if __name__ == "__main__":
    debug_symbols_from_supabase()

    # Test inputs you want to check
    debug_symbols_input('["AAPL"]')
    debug_symbols_input(["AAPL"])
