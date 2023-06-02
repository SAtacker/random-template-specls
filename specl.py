import random
import sys
import string


class TemplateSpecl:
    def __init__(
        self, number_of_specls, templ_templ_depth=0, id=random.randint(0, sys.maxsize)
    ) -> None:
        self.n_specls = number_of_specls
        self.templ_templ_depth = templ_templ_depth
        self._base_int_types = [
            "signed char",
            "unsigned char",
            "short int",
            "unsigned short int",
            "int",
            "unsigned int",
            "long int",
            "unsigned long int",
            "long long int",
            "unsigned long long int",
        ]
        self._base_bool_types = ["bool"]
        self._base_char_types = [
            "signed char",
            "unsigned char",
            "wchar_t",
            "char16_t",
        ]
        self._base_fp_types = [
            "float",
            "double",
            "long double",
        ]
        self.base_types = []
        self.base_types.extend(self._base_char_types)
        self.base_types.extend(self._base_int_types)
        self.base_types.extend(self._base_bool_types)
        self.base_types.extend(self._base_fp_types)
        self._ids = {}
        self._base_struct_id = id
        self._ids[self._base_struct_id] = -1
        self._base_decl_type_name = f"_rand_class_base_{self._base_struct_id}"
        self.base_decl = (
            "template <typename ...> struct " + self._base_decl_type_name + " { };"
        )
        self._specls_done = []  # list of speclizations done

    def _gen_random_type(self, n_specls) -> str:
        if n_specls not in self._specls_done:
            self._specls_done.append(n_specls)
            _typenames = ""
            _typename_names = ""
            for _ in range(0, n_specls):
                _typename_name_ = random.choices(string.ascii_uppercase, k=12)
                _typename_name_ = "".join(_typename_name_)
                _typenames += "typename " + _typename_name_
                _typenames += " ,"
                _typename_names += _typename_name_
                _typename_names += " ,"
            if _typenames[-1] == ",":
                _typenames = _typenames[:-1]
            if _typename_names[-1] == ",":
                _typename_names = _typename_names[:-1]
            rt_str1 = (
                "template <"
                + _typenames
                + "> struct "
                + self._base_decl_type_name
                + "<"
                + _typename_names
                + ">"
                + " { };"
            )
            temp_list = self.base_types[:]
            if len(temp_list) < n_specls:
                temp_list = [
                    self.base_types[i % len(self.base_types)]
                    for i in range(0, n_specls)
                ]
            rt_str2 = (
                rt_str1
                + "\n"
                + (
                    "template <> struct "
                    + self._base_decl_type_name
                    + "<"
                    + ",".join(temp_list[:n_specls])
                    + ">"
                    + " { };"
                )
            )
            return rt_str2
        else:
            return None

    def generate_base_type_specls(self) -> str:
        ret_str = self.base_decl + "\n"
        for depth in range(0, self.templ_templ_depth + 1):
            for specl_id in range(1, self.n_specls + 1):
                if specl_id not in self._specls_done:
                    ret_str += self._gen_random_type(specl_id)
                    ret_str += "\n"
                else:
                    continue
        return ret_str

    def generate_cpp(self) -> str:
        ret_str = ""
        for id in self._specls_done:
            temp_list = self.base_types[:]
            if len(temp_list) < id:
                temp_list = [
                    self.base_types[i % len(self.base_types)] for i in range(0, id)
                ]
            ret_str += self._base_decl_type_name
            ret_str += "<" + ",".join(temp_list[:id]) + ">"
            ret_str += " " + "".join(random.choices(string.ascii_uppercase, k=12))
            ret_str += ";\n"
        return ret_str

    def __str__(self) -> str:
        return ""
