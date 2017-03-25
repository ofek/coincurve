import os
import json
import pytest
import secp256k1

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')

from cffi import FFI

ffi = FFI()
ffi.cdef('static int nonce_function_rand(unsigned char *nonce32,'
         'const unsigned char *msg32,const unsigned char *key32,'
         'const unsigned char *algo16,void *data,unsigned int attempt);')

#The most elementary conceivable nonce function, acting
#as a passthrough: user provides random data which must be
#a valid scalar nonce. This is not ideal,
#since libsecp256k1 expects the nonce output from
#this function to result in a valid sig (s!=0), and will
#increment the counter ("attempt") and try again if it fails;
#since we don't increment the counter here, that will not succeed.
#Of course the likelihood of such an error is infinitesimal.
#TLDR this is not intended to be used in real life; use
#deterministic signatures.
ffi.set_source("_noncefunc",
"""
static int nonce_function_rand(unsigned char *nonce32,
const unsigned char *msg32,
const unsigned char *key32,
const unsigned char *algo16,
void *data,
unsigned int attempt)
{
memcpy(nonce32,data,32);
return 1;
}
""")

ffi.compile()

import _noncefunc
from _noncefunc import ffi

def test_ecdsa_with_custom_nonce():
    data = open(os.path.join(DATA, 'ecdsa_custom_nonce_sig.json')).read()
    vec = json.loads(data)['vectors']
    inst = secp256k1.PrivateKey()
    for item in vec:
        seckey = bytes(bytearray.fromhex(item['privkey']))
        msg32 = bytes(bytearray.fromhex(item['msg']))
        sig = bytes(bytearray.fromhex(item['sig']))
        randnonce = bytes(bytearray.fromhex(item['nonce']))
        inst.set_raw_privkey(seckey)
        nf = ffi.addressof(_noncefunc.lib, "nonce_function_rand")
        ndata = ffi.new("char [32]", randnonce)
        sig_raw = inst.ecdsa_sign(msg32, raw=True, custom_nonce=(nf, ndata))
        sig_check = inst.ecdsa_serialize(sig_raw)
        assert sig_check == sig
        assert inst.ecdsa_serialize(inst.ecdsa_deserialize(sig_check)) == sig_check
        assert inst.pubkey.ecdsa_verify(msg32, sig_raw, raw=True)

