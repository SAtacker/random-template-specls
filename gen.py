import os
import argparse
import subprocess
from specl import TemplateSpecl
import shutil
import tqdm
import matplotlib.pyplot as plt


def main(args):
    if os.path.exists("autogen"):
        shutil.rmtree("autogen")
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
    #     with open(os.path.join(mod_dir, "module.modulemap"), "w+") as f:
    #         f.write(
    #             """module "std" [system] {
    #   requires !windows
    #   export *
    # """
    #         )
    prev_specls = ""
    for t_index in tqdm.tqdm(range(0, args.headers)):
        tsp = TemplateSpecl(args.specls, 0, id=t_index)
        prev_specls += tsp.generate_base_types()
        if t_index >= 1:
            with open(os.path.join(mod_dir, str(t_index) + ".hpp"), "w+") as f:
                f.write(f'#include "{t_index - 1}.hpp"\n')
        with open(os.path.join(mod_dir, str(t_index) + ".hpp"), "a") as f:
            f.write(prev_specls)
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
        prev_specls = TemplateSpecl(
            args.specls, 0, id=t_index
        ).generate_base_types_specls()

    cpp_str += "\n"
    cpp_str += "}"
    with open(os.path.join(mod_dir, "main" + ".cpp"), "w+") as f:
        f.write(cpp_str)
    # with open(os.path.join(mod_dir, "module.modulemap"), "a") as f:
    #     f.write("\n}\n")

    os.mkdir(os.path.join(mod_dir, "pcms"))
    # for t_index in range(0, args.headers):
    # clang++ -std=c++17 -fmodules -ivfsoverlay ./vfs.overlay -fimplicit-module-maps -fmodules-cache-path=./pcms main.cpp
    print(f"Compiling Modules using: {args.clang_path}")
    modules_arg_string = "-fmodules -fmodule-map-file=./autogen/module.modulemap"
    prev_args = ""
    for _ in tqdm.tqdm(range(0, args.headers)):
        res = subprocess.run(
            args.clang_path
            + f"  -x c++-header -Xclang -emit-module -o autogen/pcms/{_}.pcm -fmodules autogen/module.modulemap -fmodule-name={_} -std=c++17 {prev_args}",
            capture_output=True,
            shell=True,
        )
        modules_arg_string += f" -fmodule-file={_}=./autogen/pcms/{_}.pcm "
        prev_args += f" -fmodule-file={_}=./autogen/pcms/{_}.pcm "
    # print(f"Modules command: {modules_arg_string}")
    print(f"Compiling main.cpp using: {args.clang_path}")
    avg = 0
    memory_avg = 0
    for _ in tqdm.tqdm(range(0, args.compile_runs)):
        res = subprocess.run(
            "/usr/bin/time -v "
            + args.clang_path
            + f"  -std=c++17 ./autogen/main.cpp {modules_arg_string} -Xclang -print-stats -ftime-report 2>&1",
            capture_output=True,
            shell=True,
        )
        if "error" in res.stderr.decode():
            print(f"Error in clang: {res.stderr.decode()}")
            exit(1)
        true_res = res.stdout.decode().split("Clang front-end time report")[1]
        memory_current = (
            float(
                (
                    res.stdout.decode()
                    .split("Maximum resident set size (kbytes):")[1]
                    .split("\n")[0]
                ).strip()
            )
            / 1000
        )
        memory_avg += memory_current
        total_ex_time = "".join(true_res.split("seconds")[0])
        total_ex_time = "".join(total_ex_time.split("Time:")[1])
        total_ex_time = total_ex_time.strip()
        total_ex_time = float(total_ex_time)
        avg += total_ex_time
    avg = avg / args.compile_runs
    memory_avg = memory_avg / args.compile_runs
    print(f"Avg Total ex time: {avg} | Avg Max Resident Memory: {memory_avg}")
    return avg, memory_avg


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
        "--test-runs",
        help="Number of headers to plot",
        action="store",
        default=10,
        type=int,
    )
    args_parser.add_argument(
        "--test-run-steps",
        help="Number of steps",
        action="store",
        default=10,
        type=int,
    )
    args_parser.add_argument(
        "--test-run-start",
        help="Start point for tests",
        action="store",
        default=1,
        type=int,
    )
    args_parser.add_argument(
        "--clang-path",
        help="Boolean to compile each module",
        action="store",
        default="clang++",
    )
    args = args_parser.parse_args()
    res = []
    headers = []
    args.clang_path = "clang++"
    on_disk_memory = []
    memory_resident_avg = []
    CONST = args.headers
    for i in range(args.test_run_start, CONST, args.test_run_steps):
        print(f"Iteration: {i}")
        args.headers = i
        # args.specls = i
        _res, _memory = main(args)
        res.append(_res)
        memory_resident_avg.append(_memory)
        headers.append(i)
        du_opt = subprocess.run(
            "du -sh autogen/pcms",
            capture_output=True,
            shell=True,
        )
        if "K" in du_opt.stdout.decode():
            on_disk_memory.append(float(du_opt.stdout.decode().split("K")[0]) / 1000)
        elif "M" in du_opt.stdout.decode():
            on_disk_memory.append(float(du_opt.stdout.decode().split("M")[0]))
        elif "G" in du_opt.stdout.decode():
            on_disk_memory.append(float(du_opt.stdout.decode().split("G")[0]) * 1000)

    plt.plot(headers, res, color="green")
    res_n = []
    headers_n = []
    args.clang_path = "../llvm-project/build/bin/clang++"
    on_disk_memory_n = []
    memory_resident_avg_n = []
    for i in range(args.test_run_start, CONST, args.test_run_steps):
        print(f"Iteration: {i}")
        args.headers = i
        # args.specls = i
        _res, _memory = main(args)
        res_n.append(_res)
        headers_n.append(i)
        memory_resident_avg_n.append(_memory)
        du_opt = subprocess.run(
            "du -sh autogen/pcms",
            capture_output=True,
            shell=True,
        )
        if "K" in du_opt.stdout.decode():
            on_disk_memory_n.append(float(du_opt.stdout.decode().split("K")[0]) / 1000)
        elif "M" in du_opt.stdout.decode():
            on_disk_memory_n.append(float(du_opt.stdout.decode().split("M")[0]))
        elif "G" in du_opt.stdout.decode():
            on_disk_memory_n.append(float(du_opt.stdout.decode().split("G")[0]) * 1000)
    plt.plot(headers_n, res_n, color="red")
    plt.savefig("patch_plot.png")
    plt.cla()
    plt.plot(headers_n, on_disk_memory_n, color="red")
    plt.plot(headers, on_disk_memory, color="green")
    plt.savefig("memory_patch_plot.png")
    plt.cla()
    plt.plot(headers_n, memory_resident_avg_n, color="red")
    plt.plot(headers, memory_resident_avg, color="green")
    plt.savefig("resident_memory_plot.png")
    plt.cla()
    try:
        os.remove("data_clang-14.txt")
        os.remove("data_clang_custom_patch.txt")
        os.remove("data_clang_indexes.txt")
        os.remove("data_clang_custom_patch_memory.txt")
        os.remove("data_clang_14_memory.txt")
        os.remove("data_clang_14_memory_resident.txt")
        os.remove("data_clang_custom_memory_resident.txt")
    except:
        pass
    for index, tup in enumerate(zip(res, res_n)):
        i, j = tup
        with open("data_clang-14.txt", "a") as f:
            f.write(str(i) + "\n")
        with open("data_clang_custom_patch.txt", "a") as f:
            f.write(str(j) + "\n")
        with open("data_clang_indexes.txt", "a") as f:
            f.write(str(index) + "\n")
        with open("data_clang_14_memory.txt", "a") as f:
            f.write(str(on_disk_memory[index]) + "\n")
        with open("data_clang_custom_patch_memory.txt", "a") as f:
            f.write(str(on_disk_memory_n[index]) + "\n")
        with open("data_clang_custom_memory_resident.txt", "a") as f:
            f.write(str(memory_resident_avg_n[index]) + "\n")
        with open("data_clang_14_memory_resident.txt", "a") as f:
            f.write(str(memory_resident_avg[index]) + "\n")
