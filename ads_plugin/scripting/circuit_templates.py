"""
Circuit Templates for ADS Automation
Provides high-level functions to create standard RF/Microwave topologies.
"""
import keysight.ads.de as de
from keysight.ads.de import db_uu

def create_tline_test_circuit(design_uri, width_mm, length_mm, er=4.4, h_mm=1.6):
    """
    Creates a simple microstrip test structure:
    Term1 (50 Ohm) -- MLIN -- Term2 (50 Ohm)
    Includes MSub definition.
    """
    try:
        # Open/Create the design
        design = db_uu.open_design(design_uri)
        if design is None:
            return {"status": "error", "message": f"Could not open design: {design_uri}"}

        # 1. Add MSub (Substrate Definition)
        # Positioned top-left
        msub_inst = design.add_instance("ads_rflib:MSub:symbol", (-200, 200), name="MSub1")
        if msub_inst:
            msub_inst.parameters['Er'] = str(er)
            msub_inst.parameters['H'] = f"{h_mm} mm"
            msub_inst.parameters['TanD'] = "0.02"
            msub_inst.parameters['T'] = "35 um"

        # 2. Add MLIN (Microstrip Line)
        # Positioned at (0,0)
        mlin_inst = design.add_instance("ads_rflib:MLIN:symbol", (0, 0), name="TL1")
        if mlin_inst:
            mlin_inst.parameters['W'] = f"{width_mm} mm"
            mlin_inst.parameters['L'] = f"{length_mm} mm"
            mlin_inst.parameters['Subst'] = "MSub1"

        # 3. Add Ports (Term)
        # Term 1 at the left
        term1 = design.add_instance("ads_simulation:Term:symbol", (-100, 0), name="Term1")
        if term1:
            term1.parameters['Num'] = "1"
            term1.parameters['Z'] = "50 Ohm"

        # Term 2 at the right (calculate position based on L)
        # Assuming 1mm ~ 40 mils for placement coordinate spacing
        l_offset = int(length_mm * 40) + 100
        term2 = design.add_instance("ads_simulation:Term:symbol", (l_offset, 0), name="Term2", angle=180)
        if term2:
            term2.parameters['Num'] = "2"
            term2.parameters['Z'] = "50 Ohm"

        # 4. Add Wires (Connect everything)
        # Points: (x1, y1), (x2, y2)
        design.add_wire([(-100, 0), (0, 0)]) # Term1 to TL1
        design.add_wire([(int(length_mm * 40), 0), (l_offset, 0)]) # TL1 to Term2

        # 5. Add S-Parameter Controller (for simulation)
        sp_inst = design.add_instance("ads_simulation:S_Param:symbol", (0, 300), name="SP1")
        if sp_inst:
            sp_inst.parameters['Start'] = "1.0 GHz"
            sp_inst.parameters['Stop'] = "10.0 GHz"
            sp_inst.parameters['Step'] = "0.1 GHz"

        design.save()
        return {
            "status": "success", 
            "message": f"T-Line test circuit created in {design_uri}",
            "dimensions": {"W": width_mm, "L": length_mm}
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
