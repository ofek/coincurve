# Developer Interface

-----

All objects are available directly under the root namespace `coincurve`.

::: coincurve.verify_signature

::: coincurve.PrivateKey
    options:
      members:
      - __init__
      - sign
      - sign_recoverable
      - sign_schnorr
      - ecdh
      - add
      - multiply
      - to_int
      - to_hex
      - to_pem
      - to_der
      - from_int
      - from_hex
      - from_pem
      - from_der

::: coincurve.PublicKey
    options:
      members:
      - __init__
      - verify
      - format
      - point
      - combine
      - add
      - multiply
      - combine_keys
      - from_signature_and_message
      - from_secret
      - from_valid_secret
      - from_point

::: coincurve.PublicKeyXOnly
    options:
      members:
      - __init__
      - verify
      - format
      - tweak_add
      - from_secret
      - from_valid_secret
