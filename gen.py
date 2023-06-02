import os
import argparse
import subprocess
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
    vfs_overlay = (
        """{
    "version": 0,
    "case-sensitive": "false",
    "roots": [
      {
        "external-contents": """
        + os.path.join(mod_dir, "module.module")
        + """,
        "name": "/usr/include/c++/12/module.modulemap",
        "type": "file"
      }
    ]
}"""
    )
    with open(os.path.join(mod_dir, "vfs.overlay"), "w+") as f:
        f.write(vfs_overlay)
    cpp_str = """
"""
    cpp_str += "\n".join([f'#include "{id}.hpp"' for id in range(0, args.headers)])
    cpp_str += """

int main(){
"""
    with open(os.path.join(mod_dir, "module.modulemap"), "w+") as f:
        f.write(
            """module "std" [system] {
  requires !windows
  export *
"""
        )
    for t_index in tqdm.tqdm(range(0, args.headers)):
        tsp = TemplateSpecl(args.specls, 0, id=t_index)
        with open(os.path.join(mod_dir, str(t_index) + ".hpp"), "w+") as f:
            f.write(tsp.generate_base_type_specls())
        with open(os.path.join(mod_dir, "module.modulemap"), "a") as f:
            f.write(
                """  module \""""
                + str(t_index)
                + """\" {
    export *
    header \""""
                + str(t_index)
                + ".hpp"
                + """\"
    }
"""
            )
        cpp_str += tsp.generate_cpp()

    cpp_str += "\n"
    cpp_str += "}"
    with open(os.path.join(mod_dir, "main" + ".cpp"), "w+") as f:
        f.write(cpp_str)
    with open(os.path.join(mod_dir, "module.modulemap"), "a") as f:
        f.write("\n}\n")

    os.mkdir(os.path.join(mod_dir, "pcms"))
    # for t_index in range(0, args.headers):
    # clang++ -std=c++17 -fmodules -ivfsoverlay ./vfs.overlay -fimplicit-module-maps -fmodules-cache-path=./pcms main.cpp
    print(f"Compiling using {args.clang_path}")
    avg = 0
    for _ in tqdm.tqdm(range(0, args.compile_runs)):
        res = subprocess.run(
            args.clang_path
            + "  -std=c++17 -fmodules -ivfsoverlay ./autogen/vfs.overlay -fimplicit-module-maps -fmodules-cache-path=./autogen/pcms ./autogen/main.cpp -Xclang -print-stats -ftime-report",
            capture_output=True,
            shell=True,
        )
        assert len(res.stdout) == 0
        if "error" in res.stderr.decode():
            print(f"Error in clang: {res.stderr.decode()}")
            exit(1)
        true_res = res.stderr.decode().split("Clang front-end time report")[1]
        total_ex_time = "".join(true_res.split("seconds")[0])
        total_ex_time = "".join(total_ex_time.split("Time:")[1])
        total_ex_time = total_ex_time.strip()
        total_ex_time = float(total_ex_time)
        avg += total_ex_time
    print(f"Avg Total ex time: {total_ex_time/args.compile_runs}")
    return total_ex_time


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
    args_parser.add_argument(
        "--compile-runs",
        help="Number of runs to compile",
        action="store",
        default=3,
        type=int,
    )
    args_parser.add_argument(
        "--clang-path",
        help="Boolean to compile each module",
        action="store",
        default="clang++",
    )
    args = args_parser.parse_args()
    main(args)
