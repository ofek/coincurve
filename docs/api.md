# Developer Interface

-----

All objects are available directly under the root namespace `coincurve`.

::: coincurve.verify_signature
    rendering:
      show_root_full_path: false
    selection:
      docstring_style: restructured-text

::: coincurve.PrivateKey
    rendering:
      show_root_full_path: false
    selection:
      docstring_style: restructured-text
      members:
      - __init__
      - sign
      - sign_recoverable
      - sign_schnorr
      - ecdh
      - add
      - multiply
      - to_hex
      - to_pem
      - to_der
      - to_int
      - from_hex
      - from_pem
      - from_der
      - from_int

::: coincurve.PublicKey
    rendering:
      show_root_full_path: false
    selection:
      docstring_style: restructured-text
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
      - from_point

::: coincurve.PublicKeyXOnly
    rendering:
      show_root_full_path: false
    selection:
      docstring_style: restructured-text
      members:
      - __init__
      - verify
      - format
      - add
      - from_secret
