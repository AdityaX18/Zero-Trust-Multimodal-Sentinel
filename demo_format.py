import sys, json

try:
    # Read the JSON from the curl command
    data = json.load(sys.stdin)
    
    print("\n" + "="*70)
    if "DENIED" in data.get("status", ""):
        # \033[1;91m is Bold Bright Red
        print("\033[1;91m🚨 FATAL ACTION INTERCEPTED: DENIED BY NOVA PRO 🚨\033[0m")
    else:
        # \033[1;92m is Bold Bright Green
        print("\033[1;92m✅ ACTION APPROVED\033[0m")
    print("="*70)
    
    # \033[1;93m is Bold Bright Yellow
    print("\033[1;93mMULTIMODAL REASONING:\033[0m")
    print(data.get("reason", "No reason provided."))
    print("="*70 + "\n")
    
except Exception as e:
    print(f"\033[1;91mFailed to parse API response:\033[0m {e}")
