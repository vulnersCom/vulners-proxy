import typing
import os

def import_module(base_module, submodule):
    module_name = base_module.__name__ + '.' + submodule
    return __import__(module_name, fromlist=[submodule])

class ModuleLoader:
    def __init__(self):
        self._modules = {}

    def get_modules(self, root: typing.Any):
        try:
            return self._modules[root.__name__]
        except KeyError:
            pass
        result = set()
        for base_path in root.__path__:
            for filename in os.listdir(base_path):
                module_name, ext = os.path.splitext(filename)
                if module_name == "__init__" or ext != ".py":
                    continue
                result.add(module_name)
        result = list(result)
        self._modules[root.__name__] = result
        return result

    def load_modules(self, root: typing.Any, filtered=None):
        modules = {}
        for submodule in self.get_modules(root):
            if filtered is not None and submodule not in filtered:
                continue
            modules[submodule] = import_module(root, submodule)
        return modules

    def load_classes(self, root: typing.Any, instance_of):
        classes = list()
        for submodule in self.load_modules(root).values():
            for obj in submodule.__dict__.values():
                if isinstance(obj, instance_of):
                    classes.append(obj)
        return classes