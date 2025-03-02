import argparse
import logging
import os
import re
import sys

logging.basicConfig(level=logging.ERROR)


def remove_c_comments_emptylines(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)  # Remove multi-line comments
    text = re.sub(r"//.*", "", text)  # Remove single-line comments
    return re.sub(r"\n\s*\n+", "\n", text)  # Remove empty lines


def remove_c_includes(lines):
    return [line for line in lines if not re.match(r"^\s*#include\s", line)]


def remove_special_defines(lines, defines):
    return [line for line in lines if not any(f"#define {define}" in line for define in defines)]


def apply_cffi_defines_syntax(lines):
    return [re.sub(r"#\s*define\s+(\w+).*", r"#define \1 ...", line) for line in lines]


def remove_c_ifdef(lines):
    processed_lines = []

    # The first #if is the multi-inclusion guard
    ifdef_count = -1

    for line in lines:
        stripped_line = line.rstrip()

        if re.match(r"^#\s*(if|el|endif)", stripped_line):
            stripped_line = stripped_line.replace(" ", "")
            ifdef_count += stripped_line.count("#if") - stripped_line.count("#endif")
            continue

        if ifdef_count == 0:
            processed_lines.append(stripped_line)
        elif ifdef_count < 0 and line != lines[-1]:
            msg = "Unbalanced #if/#endif preprocessor directives."
            raise ValueError(msg)

    return processed_lines


def concatenate_c_defines(lines):
    buffer = []
    processed_lines = []
    in_define = False

    for line in lines:
        stripped_line = line.rstrip()

        if (re.match(r"#\s*define", stripped_line) or in_define) and stripped_line.endswith("\\"):
            in_define = True
            buffer.append(
                re.sub(r"#\s*define", "#define", stripped_line).rstrip("\\").strip()
            )  # Normalize #define and remove trailing backslash
            continue  # Skip the rest of the loop to avoid resetting the buffer

        if in_define:
            buffer.append(stripped_line)
            processed_lines.append(" ".join(buffer))
            buffer = []  # Reset the buffer for the next definition
            in_define = False
            continue  # Skip the rest of the loop to avoid adding the line again

        processed_lines.append(stripped_line)

    return processed_lines


def remove_deprecated_functions(lines, deprecation):
    buffer = []
    processed_lines = []
    in_struct = False
    in_define = False
    brace_count = 0

    for line in lines:
        stripped_line = line.rstrip()

        if re.match(r"#\s*define", stripped_line) or in_define:
            in_define = bool(stripped_line.endswith("\\"))
            processed_lines.append(stripped_line)
            continue

        if stripped_line.startswith("struct") or re.match(r"typedef\s+struct", stripped_line) or in_struct:
            in_struct = True
            processed_lines.append(stripped_line)
            brace_count += stripped_line.count("{") - stripped_line.count("}")
            if brace_count == 0:  # End of struct block
                in_struct = False
            continue

        buffer.append(stripped_line)

        # Check for the end of a function declaration
        if stripped_line.endswith(";") and not in_struct:
            # Extend if not DEPRECATED
            if not any(d in " ".join(buffer) for d in deprecation):
                processed_lines.extend(buffer)
            buffer = []  # Reset the buffer for the next definition

    return processed_lines


def remove_function_attributes(lines, attributes):
    processed_lines = []

    for line in lines:
        stripped_line = line.rstrip()

        for attribute, replacement in attributes.items():
            # Attributes can be functions with (...), so using regular expression
            # Remove the definition
            if re.search(rf"#\s*define\s+{attribute}(\(.*\))?\b", stripped_line):
                stripped_line = None
                break

            if re.search(rf"\b{attribute}(\(.*\))?\b", stripped_line):
                stripped_line = re.sub(rf"\b{attribute}(\(.*\))?", f"{replacement}", stripped_line)
                stripped_line = stripped_line.replace(" ;", ";")
                stripped_line = stripped_line.replace("  ", " ")

        if stripped_line:
            processed_lines.append(stripped_line)

    return processed_lines


def remove_header_guard(lines, keywords):
    processed_lines = []

    for line in lines:
        stripped_line = line.rstrip()

        for keyword in keywords:
            if re.search(rf"#\s*define\s+{keyword}.*_H\b", stripped_line):
                continue
            processed_lines.append(stripped_line)

    return processed_lines


def concatenate_c_struct(lines):
    buffer = []
    processed_lines = []
    in_struct = False
    brace_count = 0

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith("struct") or re.match(r"typedef\s+struct", stripped_line) or in_struct:
            in_struct = True
            brace_count += stripped_line.count("{") - stripped_line.count("}")
            buffer.append(stripped_line)
            if brace_count == 0:  # End of struct block
                processed_lines.append(" ".join(buffer).strip())
                buffer = []  # Reset the buffer for the next definition
                in_struct = False
            continue  # Skip the rest of the loop to avoid adding the line again

        processed_lines.append(stripped_line)

    return processed_lines


def make_header_cffi_compliant(src_header_dir, src_header, cffi_dir):
    with open(os.path.join(src_header_dir, src_header), encoding="utf-8") as f:
        text = remove_c_comments_emptylines(f.read())
    lines = text.split("\n")

    lines = remove_c_includes(lines)
    lines = remove_c_ifdef(lines)
    lines = concatenate_c_defines(lines)
    lines = remove_deprecated_functions(lines, ["DEPRECATED"])
    lines = remove_header_guard(lines, ["SECP256K1"])
    lines = remove_function_attributes(
        lines,
        {
            "SECP256K1_API": "extern",
            "SECP256K1_WARN_UNUSED_RESULT": "",
            "SECP256K1_DEPRECATED": "",
            "SECP256K1_ARG_NONNULL": "",
        },
    )
    lines = remove_special_defines(
        lines,
        [
            # Deprecated flags
            "SECP256K1_CONTEXT_VERIFY",
            "SECP256K1_CONTEXT_SIGN",
            "SECP256K1_FLAGS_BIT_CONTEXT_VERIFY",
            "SECP256K1_FLAGS_BIT_CONTEXT_SIGN",
            # Testing flags
            "SECP256K1_CONTEXT_DECLASSIFY",
            "SECP256K1_FLAGS_BIT_CONTEXT_DECLASSIFY",
            # Not for direct use - That may not mean to remove them!
            #   'SECP256K1_FLAGS_TYPE_MASK',
            #   'SECP256K1_FLAGS_TYPE_CONTEXT',
            #   'SECP256K1_FLAGS_TYPE_COMPRESSION',
            #   'SECP256K1_FLAGS_BIT_COMPRESSION',
            # Not supported
            "SECP256K1_SCHNORRSIG_EXTRAPARAMS_MAGIC",
            "SECP256K1_SCHNORRSIG_EXTRAPARAMS",
        ],
    )
    lines = apply_cffi_defines_syntax(lines)

    logging.info("   Writting: %s in %s", src_header, cffi_dir)
    output_filename = os.path.join(cffi_dir, src_header)
    with open(output_filename, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a header file.")
    parser.add_argument("src_header_dir", type=str, help="The path to the header file to be processed.")
    parser.add_argument("cffi_header", type=str, help="The path where the compliant header will be written.")
    parser.add_argument("cffi_dir", type=str, help="The path where the compliant header will be written.", default=".")

    args = parser.parse_args()

    # Verify args are valid
    if not os.path.isdir(args.src_header_dir):
        logging.error("Error: Directory: %s not found.", args.src_header_dir)
        sys.exit(1)

    if not os.path.isdir(args.cffi_dir):
        logging.error("Error: Directory: %s not found.", args.cffi_dir)
        sys.exit(1)

    if not os.path.isfile(os.path.join(args.src_header_dir, args.cffi_header)):
        logging.error("Error: %s not found in %s.", args.cffi_header, args.src_header_dir)
        sys.exit(1)

    make_header_cffi_compliant(args.src_header_dir, args.cffi_header, args.cffi_dir)
