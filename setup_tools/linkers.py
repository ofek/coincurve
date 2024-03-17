import os
import sys

from setup_tools.support import has_system_lib


class SharedLinker:
    @staticmethod
    def update_link_args(compiler, libraries, libraries_dirs, extra_link_args):
        if compiler.__class__.__name__ == 'UnixCCompiler':
            extra_link_args.extend([f'-l{lib}' for lib in libraries])
            if has_system_lib():
                # This requires to add DYLD_LIBRARY_PATH to the environment
                # When repairing the wheel on MacOS (linux not tested yet)
                extra_link_args.extend([f'-L{lib}' for lib in libraries_dirs])
            elif sys.platform == 'darwin':
                extra_link_args.extend(['-Wl,-rpath,@loader_path/lib'])
            else:
                extra_link_args.extend(
                    [
                        '-Wl,-rpath,$ORIGIN/lib',
                        '-Wl,-rpath,$ORIGIN/lib64',
                    ]
                )
        elif compiler.__class__.__name__ == 'MSVCCompiler':
            for ld in libraries_dirs:
                ld = ld.replace('/', '\\')
                for lib in libraries:
                    lib_file = os.path.join(ld, f'lib{lib}.lib')
                    lib_path = [f'/LIBPATH:{ld}', f'lib{lib}.lib']
                    if os.path.exists(lib_file):
                        extra_link_args.extend(lib_path)
        else:
            raise NotImplementedError(f'Unsupported compiler: {compiler.__class__.__name__}')


class StaticLinker:
    @staticmethod
    def update_link_args(compiler, libraries, libraries_dirs, extra_link_args):
        if compiler.__class__.__name__ == 'UnixCCompiler':
            # It is possible that the library was compiled without fPIC option
            for lib in libraries:
                # On MacOS the mix static/dynamic option is different
                # It requires a -force_load <full_lib_path> option for each library
                if sys.platform == 'darwin':
                    for lib_dir in libraries_dirs:
                        if os.path.exists(os.path.join(lib_dir, f'lib{lib}.a')):
                            extra_link_args.extend(['-Wl,-force_load', os.path.join(lib_dir, f'lib{lib}.a')])
                            break
                else:
                    extra_link_args.extend(['-Wl,-Bstatic', f'-l{lib}', '-Wl,-Bdynamic'])

        elif compiler.__class__.__name__ == 'MSVCCompiler':
            for ld in libraries_dirs:
                ld = ld.replace('/', '\\')
                for lib in libraries:
                    lib_file = os.path.join(ld, f'lib{lib}.lib')
                    if os.path.exists(lib_file):
                        extra_link_args.append(lib_file)
        else:
            raise NotImplementedError(f'Unsupported compiler: {compiler.__class__.__name__}')
