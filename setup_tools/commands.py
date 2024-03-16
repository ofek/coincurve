from setuptools.command import develop, dist_info, egg_info, sdist

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None


class EggInfo(egg_info.egg_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        from setup_tools.support import has_system_lib

        if not has_system_lib():
            from support import download_library

            download_library(self)

        super().run()


class DistInfo(dist_info.dist_info):
    def run(self):
        # Ensure library has been downloaded (sdist might have been skipped)
        from setup_tools.support import has_system_lib

        if not has_system_lib():
            from support import download_library

            download_library(self)

        super().run()


class Sdist(sdist.sdist):
    def run(self):
        from setup_tools.support import has_system_lib

        if not has_system_lib():
            from support import download_library

            download_library(self)
        super().run()


class Develop(develop.develop):
    def run(self):
        from setup_tools.support import has_system_lib

        if not has_system_lib():
            raise RuntimeError(
                "This library is not usable in 'develop' mode when using the "
                'bundled libsecp256k1. See README for details.'
            )
        super().run()


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    _bdist_wheel = None


if _bdist_wheel:

    class BdistWheel(_bdist_wheel):
        def run(self):
            from setup_tools.support import has_system_lib

            if not has_system_lib():
                from setup_tools.support import download_library

                download_library(self)
            super().run()

else:
    BdistWheel = None
