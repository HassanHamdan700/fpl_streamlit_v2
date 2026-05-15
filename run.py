import sys
import asyncio

# The issue was that setting the loop policy AFTER creating the loop
# cleared the event loop association. We must set the policy first!
if sys.platform == 'win32':
    import warnings
    # Ignore the deprecation warning for Python 3.14+
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Now we safely set the event loop for the current policy
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import streamlit.web.cli as stcli

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "main.py"]
    sys.exit(stcli.main())
