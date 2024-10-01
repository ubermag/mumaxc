import numbers

import discretisedfield as df
import micromagneticmodel as mm
import numpy as np

import mumax3c as mc


def driver_script(
    driver, system, compute=None, ovf_format="bin4", mx3_txt=None, **kwargs
):
    mx3 = "tableadd(E_total)\n"
    mx3 += "tableadd(dt)\n"
    mx3 += "tableadd(maxtorque)\n"

    if isinstance(driver, mc.MinDriver):
        for attr, value in driver:
            if attr != "evolver":
                mx3 += f"{attr} = {value}\n"

        if mx3_txt is not None:
            mx3 += "\n"
            mx3 += mx3_txt
            mx3 += "\n"
        mx3 += "minimize()\n\n"
        mx3 += "save(m_full)\n"
        mx3 += "tablesave()\n\n"

    if isinstance(driver, mc.RelaxDriver):
        if system.dynamics.get(type=mm.Damping):
            alpha = system.dynamics.get(type=mm.Damping)[0].alpha
            mx3 += f"alpha = {alpha}\n"

        for attr, value in driver:
            if attr != "evolver":
                mx3 += f"{attr} = {value}\n"

        if mx3_txt is not None:
            mx3 += "\n"
            mx3 += mx3_txt
            mx3 += "\n"
        mx3 += "relax()\n\n"
        mx3 += "save(m_full)\n"
        mx3 += "tablesave()\n\n"

    if isinstance(driver, mc.TimeDriver):
        # Need temperature only here
        if system.T > 0:
            mx3 += f"Temp = {system.T}\n"
        # Extract dynamics equation parameters.
        gamma0 = (
            precession[0].gamma0
            if (precession := system.dynamics.get(type=mm.Precession))
            else 0
        )
        if system.dynamics.get(type=mm.Damping):
            alpha = system.dynamics.damping.alpha
        else:
            alpha = 0

        mx3 += f"alpha = {alpha}\n"
        if not gamma0:
            mx3 += "doprecess = false\n"
        else:
            mx3 += f"gammaLL = {gamma0/mm.consts.mu0}\n"
            mx3 += "doprecess = true\n"

        if system.dynamics.get(type=mm.ZhangLi):
            (zh_li_term,) = system.dynamics.get(type=mm.ZhangLi)
            if isinstance(zh_li_term.u, df.Field) and zh_li_term.u.nvdim == 3:
                u = zh_li_term.u
            elif isinstance(zh_li_term.u, df.Field) and zh_li_term.u.nvdim == 1:
                zero_field = df.Field(
                    mesh=system.m.mesh,
                    nvdim=1,
                    value=0.0,
                )
                u = zh_li_term.u << zero_field << zero_field
            elif isinstance(zh_li_term.u, numbers.Real):
                u = df.Field(
                    mesh=system.m.mesh,
                    nvdim=3,
                    value=(zh_li_term.u, 0.0, 0.0),
                )
            elif isinstance(zh_li_term.u, dict):
                if isinstance(list(zh_li_term.u.values())[0], numbers.Real):
                    u_values = {
                        key: (value, 0.0, 0.0) for key, value in zh_li_term.u.items()
                    }
                else:
                    u_values = zh_li_term.u
                u = df.Field(
                    mesh=system.m.mesh,
                    nvdim=3,
                    value=u_values,
                )
            else:  # array_like
                u = df.Field(mesh=system.m.mesh, nvdim=3, value=zh_li_term.u)

            mu_B = mm.consts.e * mm.consts.hbar / (2.0 * mm.consts.me)

            j = -np.multiply(
                u * 2 * (1 + zh_li_term.beta**2) * mm.consts.e / (mm.consts.g * mu_B),
                system.m.norm,
            )
            j.to_file("j.ovf", representation=ovf_format)
            mx3 += f"Xi = {zh_li_term.beta}\n"
            mx3 += "Pol = 1\n"  # Current polarization is 1.
            mx3 += 'J.add(LoadFile("j.ovf"), 1)\n'  # 1 means constant in time.

        mx3 += "setsolver(5)\n"
        mx3 += "fixDt = 0\n\n"

        if mx3_txt is not None:
            mx3 += "\n"
            mx3 += mx3_txt
            mx3 += "\n"

        t, n = kwargs["t"], kwargs["n"]

        mx3 += f"for snap_counter:=0; snap_counter<{n}; snap_counter++{{\n"
        mx3 += f"    run({t/n})\n"
        mx3 += "    save(m_full)\n"
        mx3 += "    tablesave()\n"
        mx3 += "}"

    return mx3
