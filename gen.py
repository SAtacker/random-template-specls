import os
import argparse
from specl import TemplateSpecl
import shutil
import tqdm


def main(args):
    if os.path.exists("autogen"):
        shutil.rmtree("autogen")
    else:
        os.mkdir("autogen")
    mod_dir = "autogen"
    os.mkdir(mod_dir)
    cpp_str = """#include <string>
#include <vector>
"""
    cpp_str += "\n".join([f'#include "{id}.hpp"' for id in range(0, args.headers)])
    cpp_str += """

int main(){
"""
    for t_index in tqdm.tqdm(range(0, args.headers)):
        tsp = TemplateSpecl(args.specls, 0, id=t_index)
        with open(os.path.join(mod_dir, str(t_index) + ".hpp"), "w+") as f:
            f.write(tsp.generate_base_type_specls())
        cpp_str += tsp.generate_cpp()

    cpp_str += "\n"
    cpp_str += "}"
    with open(os.path.join(mod_dir, "main" + ".cpp"), "w+") as f:
        f.write(cpp_str)


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--specls",
        help="Specify number of Template Specializations",
        action="store",
        default=5,
        type=int,
    )
    args_parser.add_argument(
        "--headers",
        help="Number of Headers",
        action="store",
        default=1,
        type=int,
    )
    args = args_parser.parse_args()
    main(args)
