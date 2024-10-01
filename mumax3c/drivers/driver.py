import abc
import pathlib

import discretisedfield as df
import micromagneticmodel as mm
import ubermagtable as ut
import ubermagutil as uu

import mumax3c as mc


class Driver(mm.ExternalDriver):
    """Driver base class."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, "evolver"):
            self.autoselect_evolver = False
        else:
            self.autoselect_evolver = True

    @abc.abstractmethod
    def _checkargs(self, **kwargs):
        """Abstract method for checking arguments."""

    def drive_kwargs_setup(self, drive_kwargs):
        """Additional keyword arguments allowed for drive.

        This function tests additional keyword arguments that have been passed to the
        ``drive`` method (it is not intended for direct use). A drive in mumax3c can
        accept the following additional keyword arguments.

        Parameters
        ----------
        abspath : bool, optional

            If ``True`` absolute paths for all input files (e.g. the initial
            magnetisation) are used in the mx3 file. If ``False`` relative paths are
            used. Defaults to ``True``.

        """
        self._checkargs(**drive_kwargs)
        drive_kwargs.setdefault("abspath", True)

        # TODO OOMMF support additional arguments; are there equivalent options in mumax
        # fixed_subregions = None  # mumax?
        # compute = None  # mumax?
        # output_step = False  # mumax?

    def schedule_kwargs_setup(self, schedule_kwargs):
        """Additional keyword arguments allowed for schedule.

        This function tests additional keyword arguments that have been passed to the
        ``schedule`` method (it is not intended for direct use). A drive in oommfc can
        accept the following additional keyword arguments.

        It is the user's responsibility to ensure that OOMMF can be executed from the
        scheduled job.

        Parameters
        ----------
        abspath : bool, optional

            If ``True`` absolute paths for all input files (e.g. the initial
            magnetisation) are used in the mx3 file. If ``False`` relative paths are
            used. Defaults to ``True``.

        """
        self._checkargs(**schedule_kwargs)
        schedule_kwargs.setdefault("abspath", True)

    def _write_input_files(self, system, **kwargs):
        self.write_mx3(system, **kwargs)

    def write_mx3(
        self,
        system,
        dirname=".",
        ovf_format="bin8",
        mx3_txt=None,
        abspath=True,
        **kwargs,
    ):
        """Write the mx3 file and related files.

        Takes ``micromagneticmodel.System`` and write the mx3 file (and related files)
        to drive it in the phase space. The files are written directly to directory
        ``dirname`` (if not specified the current working directory). No additional
        subdirectiories are created.

        This method accepts any other arguments that could be required by the
        specific driver.

        Users are generally not encouraged to use this method directly. Instead
        ``Driver.drive``, ``Driver.schedule``, or ``mc.schedule`` should be used to
        write the files an run the simulation. This method is provided to give advanced
        users full flexibility.

        Parameters
        ----------
        system : micromagneticmodel.System

            System object to be driven.

        dirname : str, optional

            Name of a directory in which the input files are stored.
            If not specified the current workinng
            directory is used.

        ovf_format : str

            TODO UPDATE TO THE SUPPORTED MUMAX FILE TYPES
            Format of the magnetisation output files written by mumax3. Can be
            one of ``'bin8'`` (binary, double precision), ``'bin4'`` (binary,
            single precision) or ``'txt'`` (text-based, double precision).
            Defaults to ``'bin8'``.

        mx3_txt : str, optional

            Directly input string into mx3 file at a position immediately
            before the type of driver explicity written.


        abspath : bool, optional

            If ``abspath=True`` absolute paths for additional input files (e.g. initial
            magnetisation) are written to the mx3 file. If ``abspath=False`` only
            filenames are written to the file. Relative files require mumax3 to be run
            from inside the directory containing the mx3 and other input files.

        """
        with uu.changedir(dirname):
            mx3 = mc.scripts.system_script(
                system, ovf_format=ovf_format, abspath=abspath
            )
            mx3 += mc.scripts.driver_script(
                self,
                system,
                compute=None,  # TODO does mumax3 support compute?
                ovf_format=ovf_format,
                mx3_txt=mx3_txt,
                **kwargs,
            )
            with open(self._mx3filename(system), "w", encoding="utf-8") as mx3file:
                mx3file.write(mx3)

            # Generate and save json info file for a drive (not compute).
            if True:  # compute is None:  # TODO does mumxa3 support compute?
                self._write_info_json(system, **kwargs)

        # TODO if self/system is modified for mx3 creation reset it here
        delattr(system, "region_relator")

    def _call(self, system, runner, verbose=1, dry_run=False, **kwargs):
        if runner is None:
            runner = mc.runner.runner
        if dry_run:
            return runner.call(argstr=self._mx3filename(system), dry_run=True)
        else:
            runner.call(
                argstr=self._mx3filename(system),
                verbose=verbose,
                total=kwargs.get("n"),
                glob_name=f"{system.name}.out/m_full*.ovf",
            )

    def _schedule_commands(self, system, runner):
        if runner is None:
            runner = mc.runner.runner
        return [
            runner._call(argstr=self._mx3filename(system), dry_run=True),
        ]

    def _read_data(self, system):
        # Update system's magnetisation. An example .ovf filename: m_full000000.ovf
        ovffiles = pathlib.Path(f"{system.name}.out").glob("m_full*.ovf")
        lastovffile = sorted(ovffiles)[-1]
        # pass Field.array instead of Field for better performance
        # Mumax3 norm changes so need to set back to old norm
        norm_field = system.m.norm
        system.m.array = df.Field.from_file(str(lastovffile)).array
        system.m.norm = norm_field

        system.table = ut.Table.fromfile(
            str(pathlib.Path(f"{system.name}.out/table.txt")), x=self._x
        )

    @staticmethod
    def _mx3filename(system):
        return f"{system.name}.mx3"
