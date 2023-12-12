import re

def extract_defines(header_file_path):
    # Define a regular expression pattern to match #define macros.
    # This pattern aims to match:
    # - #define keyword (possibly with leading whitespaces)
    # - macro name
    # - (optionally) the value assigned to the macro
    pattern = re.compile(r'^\s*#define\s+([A-Za-z_]\w*)\s*(.*)?')

    defines = {}

    with open(header_file_path, 'r') as f:
        for line in f:
            match = pattern.match(line)
            if match:
                macro_name, macro_value = match.groups()
                defines[macro_name] = macro_value.strip() if macro_value else None

    return defines

header_file_path = 'AppUpdaterConfig.h'
macros = extract_defines(header_file_path)

for name, value in macros.items():
    print(f"{name} = {value}")
