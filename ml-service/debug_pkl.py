"""
Extract XGBoost model from pickle and reload using XGBoosterUnserializeFromBuffer directly.
The bytearray inside the pkl IS the serialized booster — we just need to call the right API.
"""
import pickle, pathlib, ctypes
import xgboost as xgb
import xgboost.core as xgb_core

p = pathlib.Path('../scarlet_demand_model/demand_model.pkl').resolve()

# Step 1: extract the sklearn wrapper state (XGBRegressor)
# The wrapper's __getstate__ stores: {'__pyx_state': ..., or normal sklearn state}
# Let's get the whole XGBRegressor state without calling Booster.__setstate__
original_booster_setstate = xgb_core.Booster.__setstate__

captured_booster_state = {}

def noop_booster_setstate(self, state):
    captured_booster_state['state'] = state
    # Don't call original — just save state
    # We'll reconstruct manually
    pass

xgb_core.Booster.__setstate__ = noop_booster_setstate

wrapper_obj = None
try:
    with open(p, 'rb') as f:
        wrapper_obj = pickle.load(f)
    print('Wrapper loaded:', type(wrapper_obj).__name__)
except Exception as e:
    print('Wrapper load error:', e)

xgb_core.Booster.__setstate__ = original_booster_setstate

if captured_booster_state:
    state = captured_booster_state['state']
    raw_bytes = bytes(state['handle'])
    print('Got raw bytes length:', len(raw_bytes))
    print('First 8 bytes:', raw_bytes[:8].hex())
    
    # Try XGBoosterUnserializeFromBuffer directly
    handle = ctypes.c_void_p()
    xgb_core._check_call(xgb_core._LIB.XGBoosterCreate(None, 0, ctypes.byref(handle)))
    
    buf = (ctypes.c_char * len(raw_bytes))(*raw_bytes)
    ret = xgb_core._LIB.XGBoosterUnserializeFromBuffer(handle, buf, len(raw_bytes))
    print('XGBoosterUnserializeFromBuffer return code:', ret)
    if ret == 0:
        print('SUCCESS! Booster deserialized.')
        # Now attach to a Booster object
        booster = xgb.Booster()
        booster.handle = handle
        
        # Attach to the wrapper
        wrapper_obj._Booster = booster
        import numpy as np
        x = np.zeros((1, 37), dtype=np.float32)
        pred = wrapper_obj.predict(x)
        print('Test prediction:', pred)
    else:
        xgb_core._check_call(ret)  # will raise

if wrapper_obj:
    print('Wrapper object type:', type(wrapper_obj).__name__)
    print('Wrapper attributes:', [a for a in dir(wrapper_obj) if not a.startswith('__')][:10])
