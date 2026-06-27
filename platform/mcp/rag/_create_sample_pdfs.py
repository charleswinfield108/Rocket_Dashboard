"""
Generate the six maintenance reference PDFs used as RAG knowledge sources.

Run once from platform/mcp/rag/:
    python3 _create_sample_pdfs.py

Writes into docs/ alongside this script.
Each PDF uses clear section headings (## prefix) so the PDF chunker
can split on them rather than falling back to page boundaries.
"""

from pathlib import Path
from fpdf import FPDF


class _SectionPDF(FPDF):
    """FPDF subclass with consistent header/footer and a section-heading helper."""

    def __init__(self, title: str):
        super().__init__()
        self._doc_title = title
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 6, "Rocket Elevators - Ontario Fleet Technical Reference", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(8)

    def section(self, heading: str) -> None:
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        # Prefix with ## so the chunker can detect headings
        self.cell(0, 8, f"## {heading}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, text)
        self.ln(2)


#  1. Hydraulic Maintenance 

def _hydraulic_maintenance(out: Path) -> None:
    pdf = _SectionPDF("Hydraulic Elevator Maintenance Manual")

    pdf.section("Overview")
    pdf.body(
        "Hydraulic elevators use a fluid-driven piston to raise and lower the cab. "
        "Routine maintenance focuses on fluid integrity, pump condition, cylinder seals, "
        "and control valve operation. TSSA requires a full hydraulic test every five years "
        "and annual oil sampling for in-ground cylinders."
    )

    pdf.section("Hydraulic Fluid - Inspection and Change Intervals")
    pdf.body(
        "Check fluid level monthly. The fluid should be clear to amber with no milky "
        "discolouration (which indicates water ingress). Sample the fluid annually; "
        "test for viscosity, acid number, and water content per ASTM D4378. "
        "Replace fluid when viscosity exceeds 20% of original grade or acid number "
        "exceeds 2.0 mg KOH/g. Dispose of used hydraulic oil as Class 3A hazardous "
        "waste - never drain into sewers."
    )

    pdf.section("Hydraulic Power Unit - Pump and Motor")
    pdf.body(
        "Inspect the pump coupling and motor mounts quarterly. Listen for cavitation "
        "(high-pitched whine at start of UP travel) - this indicates low fluid or a "
        "clogged suction filter. Replace the suction strainer annually. Check motor "
        "amperage draw against nameplate: sustained over-amperage accelerates winding "
        "failure. Re-grease motor bearings every 2,000 operating hours with NLGI Grade 2 "
        "lithium-complex grease."
    )

    pdf.section("Control Valve - Adjustment and Testing")
    pdf.body(
        "The control valve governs up-direction speed, down-direction speed, and pressure "
        "relief. Adjust lowering speed (down valve) so the car decelerates smoothly into "
        "each landing - typical target is 0.1 m/s at final approach. The pressure relief "
        "valve must be set to no more than 125% of working pressure per ASME A17.1 "
        "Section 3.19. Test annually by closing the main stop valve and running the pump: "
        "relief must open cleanly without chatter."
    )

    pdf.section("Cylinder and Piston Seal Inspection")
    pdf.body(
        "For above-ground cylinders, inspect the piston rod seal annually for weeping. "
        "A slow seep (< 1 drop / 10 minutes) is acceptable; a drip requires seal "
        "replacement within 30 days. For single-bottom in-ground cylinders, conduct an "
        "oil sampling program per CAN/CSA B44 and monitor for groundwater contamination. "
        "If a cylinder failure is suspected, shut the elevator down and notify TSSA before "
        "any excavation begins."
    )

    pdf.section("Pressure Test Procedure")
    pdf.body(
        "1. Load the car to 125% of rated capacity.\n"
        "2. Close the main stop valve.\n"
        "3. Run the pump to achieve 125% of working pressure.\n"
        "4. Hold for five minutes - pressure must not drop more than 5%.\n"
        "5. Open main stop valve; lower car at rated speed, check levelling.\n"
        "6. Record results on TSSA Form EL-HYD-01."
    )

    pdf.section("Common Hydraulic Faults and Remedies")
    pdf.body(
        "Slow down travel: Check fluid viscosity, inspect suction filter, verify motor voltage.\n"
        "Car creeps down (levelling drift): Adjust or replace down valve, check for seat wear.\n"
        "Rough ride: Air in system - bleed via bleeder screw at top of cylinder.\n"
        "Oil on pit floor: Inspect power unit connections, cylinder base seal, return-line fittings."
    )

    pdf.output(str(out))


#  2. Traction Troubleshooting 

def _traction_troubleshooting(out: Path) -> None:
    pdf = _SectionPDF("Traction Elevator Troubleshooting Guide")

    pdf.section("Overview")
    pdf.body(
        "Traction elevators use a sheave-and-rope system driven by an AC or DC motor. "
        "Faults typically originate in the machine room (motor, controller, brakes, "
        "sheave) or in the hoistway (ropes, counterweight, safeties, guide rails). "
        "This guide addresses the most common symptoms encountered on Ontario fleet units."
    )

    pdf.section("Rough Ride - Diagnosis")
    pdf.body(
        "Rough ride is the most frequent complaint. Work through causes in order:\n"
        "1. Guide rail alignment: check with a plumb line - rails must be within 3 mm "
        "of plumb over any 5 m section.\n"
        "2. Guide shoe wear: roller guides should have < 1 mm play; slide guides require "
        "greasing every 3 months.\n"
        "3. Rope tension equalization: check with a rope-tension meter - tension between "
        "any two ropes must be within 10% of each other.\n"
        "4. Sheave groove wear: measure groove depth with a groove gauge; regrind or "
        "replace sheave when groove depth exceeds 3 mm.\n"
        "5. Motor/controller: check for hunting in the drive - tune the V/Hz ratio or "
        "PID gains in the drive controller."
    )

    pdf.section("Door Malfunctions")
    pdf.body(
        "Doors are responsible for over 40% of all traction elevator incidents. "
        "Check the door operator belt or chain for wear and tension monthly. "
        "Door close force must not exceed 135 N (ASME A17.1 2.1.3.3). "
        "Test the door reversal device: place a 6 kg block in the door path - "
        "doors must reverse before contact force reaches 67 N. "
        "Clean door tracks quarterly; a single piece of debris can cause nuisance "
        "calls and entrapments."
    )

    pdf.section("Brake Adjustment")
    pdf.body(
        "The electromagnetic brake must hold 125% of rated load when set. "
        "Inspect brake linings for wear (replace at 50% lining thickness) and "
        "for oil contamination (zero tolerance - clean with brake cleaner, identify "
        "and fix oil source). Adjust brake air gap to manufacturer specification "
        "(typically 0.3 - 0.5 mm). Brake release should be smooth; a loud clunk "
        "indicates excessive gap or worn drum surface."
    )

    pdf.section("Motor and Drive Faults")
    pdf.body(
        "DC motors: check commutator for pitting, brush length (replace at 25% of new), "
        "and brush spring pressure. Clean commutator with commutator stone - never sandpaper.\n"
        "AC gearless: check encoder coupling for fretting, verify encoder cable shield "
        "is grounded at one end only. Drive fault codes beginning F0xx are typically "
        "encoder-related; F3xx indicate overcurrent - check motor insulation resistance "
        "(must be > 1 M to ground at 500 V megger)."
    )

    pdf.section("Governor and Safety System")
    pdf.body(
        "Perform governor trip test annually per ASME A17.1 Section 2.17. "
        "Governor trip speed must be within 10% of nameplate value. "
        "After any safety application, a licensed mechanic must reset the safety "
        "wedges before the elevator is returned to service - do not use the "
        "inspection drive to re-lift a car on set safeties."
    )

    pdf.output(str(out))


#  3. Safety Code Quick Reference 

def _safety_code(out: Path) -> None:
    pdf = _SectionPDF("Safety Code Quick Reference - ASME A17.1 / CAN/CSA B44")

    pdf.section("Overview")
    pdf.body(
        "This document summarises key ASME A17.1-2019 / CAN/CSA B44-19 requirements "
        "relevant to Ontario elevator compliance inspections. Always consult the full "
        "standard for enforcement decisions. References are to section numbers."
    )

    pdf.section("Load and Speed Requirements")
    pdf.body(
        "2.16.1 - Rated load: Passenger elevators must be designed for 272 kg/m2 of "
        "net platform area, not less than 454 kg total.\n"
        "2.16.3 - Contract speed must not exceed 10% above rated speed under no-load.\n"
        "3.19.1 - Relief valve setting: not more than 125% of working pressure."
    )

    pdf.section("Safety Device Tests (Periodic)")
    pdf.body(
        "8.6.4.1 - Safety and governor test: required every five years for traction "
        "elevators; every hydraulic test cycle for hydraulic elevators.\n"
        "8.6.5 - Buffer test: required at full contract speed with 100% load (or "
        "counterweight buffer test with empty car at contract speed).\n"
        "8.11.1 - Oil buffer recharge: within four hours of test completion."
    )

    pdf.section("Door Locking and Closing Force")
    pdf.body(
        "2.1.3.3 - Kinetic energy of closing door must not exceed 3.5 J.\n"
        "2.1.3.4 - Maximum closing force at 25 mm from fully closed: 133 N.\n"
        "2.12.5 - Hoistway access doors must be self-closing and self-locking; "
        "can only be opened from the hoistway side by an authorized person."
    )

    pdf.section("Fire Service Operation")
    pdf.body(
        "2.27.2 - Phase I recall: on smoke detector activation, elevator must return "
        "to primary landing (or alternate) within 60 seconds. Doors must open and "
        "remain open. Car must not respond to car calls.\n"
        "2.27.3 - Phase II operation: firefighter toggle enables manual operation. "
        "Door open button must keep doors open. Test annually."
    )

    pdf.section("Clearances - Pit and Overhead")
    pdf.body(
        "2.2.1 - Pit depth: minimum 1050 mm below lowest landing sill.\n"
        "2.2.2 - Overhead: minimum clearance from top of car to overhead structure "
        "when car is at top landing with full-speed safety test in effect.\n"
        "2.2.5 - No projections in pit other than buffers, guide rails, "
        "hydraulic cylinders, and pit equipment."
    )

    pdf.section("Maintenance Requirement Summary")
    pdf.body(
        "8.6.1 - Periodic inspections: every 12 months for all elevating devices.\n"
        "8.6.2 - Follow-up inspections: required within 60 days of a deficiency order.\n"
        "8.11 - Maintenance records must be retained at the premises for 3 years "
        "and made available to TSSA inspectors on request."
    )

    pdf.output(str(out))


#  4. Inspection Types 

def _inspection_types(out: Path) -> None:
    pdf = _SectionPDF("Inspection Types - TSSA Ontario Elevator Program")

    pdf.section("Overview")
    pdf.body(
        "The Technical Standards and Safety Authority (TSSA) administers five categories "
        "of inspection for elevating devices in Ontario. Each type has distinct triggering "
        "conditions, documentation requirements, and pass/fail criteria."
    )

    pdf.section("Periodic Inspection")
    pdf.body(
        "Trigger: Annual cycle for all licensed devices.\n"
        "Scope: Full visual and operational inspection of all safety systems, "
        "doors, buffers, safeties, interlocks, and control systems.\n"
        "Outcome codes: Passed, Follow up (minor deficiency), Follow up Major, "
        "Shutdown (immediate hazard).\n"
        "Timeline: Device must be re-inspected within 60 days of a Follow up order "
        "and immediately upon correction of a Shutdown order."
    )

    pdf.section("Follow-Up Inspection")
    pdf.body(
        "Trigger: Issued after a Periodic or Initial inspection results in a deficiency order.\n"
        "Scope: Limited to the specific deficiency items noted in the order.\n"
        "Documentation: Inspector must reference the original order number. "
        "Owner must certify in writing that all cited deficiencies have been corrected "
        "before the follow-up visit is booked."
    )

    pdf.section("Initial / Pre-Open Inspection")
    pdf.body(
        "Trigger: New installation or reinstatement after more than 12 months out of service.\n"
        "Scope: Complete inspection against current code - no grandfather provisions apply "
        "to newly installed equipment. Includes all tests specified in ASME A17.1 Section 8.10.\n"
        "Outcome: Device receives its first operating licence upon passing."
    )

    pdf.section("Special Inspection")
    pdf.body(
        "Trigger: Incident, complaint, or TSSA directive.\n"
        "Scope: Directed by the issuing TSSA officer - may be limited to specific "
        "components or may constitute a full periodic inspection.\n"
        "Authority: TSSA may issue a Shutdown order on-site if an imminent hazard is found. "
        "Owner has the right to appeal within 30 days."
    )

    pdf.section("Alteration Inspection")
    pdf.body(
        "Trigger: Any work classified as an alteration under CAN/CSA B44 Appendix E.\n"
        "Examples: Control system replacement, cab enlargement, drive conversion, "
        "rope replacement on gearless traction.\n"
        "Process: Alteration must be registered with TSSA Design before work begins. "
        "Post-alteration inspection required before the device is returned to service. "
        "Status in the TSSA database will show 'Pending Follow Up' until inspection passes."
    )

    pdf.section("Documentation Requirements")
    pdf.body(
        "The current operating licence must be posted in the elevator machine room or "
        "on the landing door (for winding drum or hydraulic units with no machine room). "
        "Maintenance logs must record: date, technician licence number, work performed, "
        "and parts replaced. Logs must be available at the premises for three years."
    )

    pdf.output(str(out))


#  5. Common Failure Modes 

def _common_failure_modes(out: Path) -> None:
    pdf = _SectionPDF("Common Elevator Failure Modes - Ontario Fleet Analysis")

    pdf.section("Overview")
    pdf.body(
        "Based on TSSA incident and inspection data from the Ontario elevator fleet, "
        "this document describes the ten most common failure modes, their root causes, "
        "and recommended preventive actions. Data reflects 2010-2018 incident reports."
    )

    pdf.section("1. Utility and Power Failures")
    pdf.body(
        "Most frequent cause in the Ontario dataset (> 35% of incidents classified "
        "with a root cause). Power interruptions strand passengers and can trigger "
        "uncontrolled descent on older DC systems without battery backup.\n"
        "Prevention: Install UPS for door operator and lighting circuits; verify "
        "ARD (Automatic Rescue Device) operation annually."
    )

    pdf.section("2. Defective or Failed Components")
    pdf.body(
        "Second most common category. Includes door operator failures, relay contacts, "
        "selector tapes, and position encoders.\n"
        "Prevention: Implement a predictive maintenance schedule tracking component "
        "age against MTBF; replace door operators at 150,000 cycles or 15 years."
    )

    pdf.section("3. Door-Related Entrapments")
    pdf.body(
        "Doors that fail to open at landings are the primary entrapment cause. "
        "Causes include worn cam rollers, misaligned door sills, broken vane couplers, "
        "and faulty door zone sensors.\n"
        "Prevention: Clean and lubricate door tracks monthly; test door open/close "
        "force and reversal device quarterly."
    )

    pdf.section("4. Levelling and Stopping Accuracy")
    pdf.body(
        "Poor levelling (car floor more than 12 mm from landing sill) is a trip hazard "
        "and a TSSA deficiency. Common causes: worn selector tape, incorrect speed "
        "profile parameters, or brake adjustment drift.\n"
        "Prevention: Check levelling at all landings during each maintenance visit; "
        "re-calibrate the drive speed profile when levelling error exceeds 6 mm."
    )

    pdf.section("5. Rope and Chain Wear")
    pdf.body(
        "Hoist ropes with > 10 broken wires per lay length, or outer wire wear > 1/3 "
        "of original diameter, must be replaced per ASME A17.1 Section 8.6.7.\n"
        "Prevention: Lubricate ropes with a penetrating lubricant annually; measure "
        "rope diameter at multiple points every two years."
    )

    pdf.section("6. Hydraulic Leaks and Seal Failures")
    pdf.body(
        "Oil leaks in the machine room or pit are a fire hazard and an environmental "
        "violation. In-ground cylinder failures can contaminate soil and groundwater.\n"
        "Prevention: Annual oil sampling; install double-bottom cylinders during "
        "any cylinder replacement; maintain an oil containment tray under the power unit."
    )

    pdf.section("7. Vandalism and Misuse")
    pdf.body(
        "Approximately 0.5% of Ontario incidents are classified as vandalism, sabotage, "
        "or theft. Emergency phones are a frequent target; forced door openings damage "
        "interlock mechanisms.\n"
        "Prevention: Install tamper-resistant emergency phone housings; review CCTV "
        "footage after any unexplained fault cluster."
    )

    pdf.section("8. Environmental - Weather and Flooding")
    pdf.body(
        "Flooding from roof drains, burst pipes, and spring thaw accounts for a "
        "significant cluster of incidents in the January-March period.\n"
        "Prevention: Inspect pit drainage pump annually before winter; seal penetrations "
        "in the pit wall where water intrusion is a risk."
    )

    pdf.output(str(out))


#  6. Emergency Response 

def _emergency_response(out: Path) -> None:
    pdf = _SectionPDF("Emergency Response Procedures - Elevating Devices")

    pdf.section("Overview")
    pdf.body(
        "This document sets out the immediate response procedures for the five most "
        "common emergency conditions on Ontario elevating devices. All field technicians "
        "must be familiar with these procedures. For life-safety emergencies, call 911 "
        "before any other action."
    )

    pdf.section("Passenger Entrapment")
    pdf.body(
        "1. Establish voice contact with entrapped passengers immediately via the "
        "emergency telephone or intercom.\n"
        "2. Advise passengers to stay calm, stay in the car, and do not attempt "
        "to force doors open or climb out.\n"
        "3. Dispatch a licensed mechanic - target arrival within 30 minutes for "
        "occupied buildings; 60 minutes for after-hours.\n"
        "4. If medical emergency is reported, call 911; advise fire department of "
        "floor location and number of passengers.\n"
        "5. Mechanic must use inspection drive to bring car to nearest landing "
        "before manually opening doors - never force landing doors with car "
        "between landings."
    )

    pdf.section("Power Failure")
    pdf.body(
        "1. If the building has an emergency generator, verify it has started and "
        "check whether the elevator is on emergency power circuit.\n"
        "2. If ARD (Automatic Rescue Device) is installed, it will automatically "
        "move the car to the nearest landing and open doors - verify within 5 minutes.\n"
        "3. If no ARD: dispatch mechanic; use battery-powered inspection unit if available.\n"
        "4. Do not restore building power while mechanic is in the hoistway."
    )

    pdf.section("Fire Service Mode Failure")
    pdf.body(
        "If a fire alarm activates and the elevator does not recall to the primary landing:\n"
        "1. Manually activate Phase I by turning the key switch at the lobby to ON.\n"
        "2. If the elevator still does not return, shut the elevator down and call TSSA.\n"
        "3. Do not attempt to use the elevator for evacuation - fire service operation "
        "is for trained fire department personnel only.\n"
        "4. Notify building fire safety plan coordinator immediately."
    )

    pdf.section("Uncontrolled Movement / Overspeed")
    pdf.body(
        "If a car is reported to have moved unexpectedly or at abnormal speed:\n"
        "1. Take the elevator out of service immediately - do not run in Normal mode.\n"
        "2. Inspect governor trip mechanism, safety wedges, and brake for signs of "
        "operation (wear marks, displaced parts).\n"
        "3. Do not return the elevator to service until a licensed mechanic has "
        "confirmed the cause and corrected it.\n"
        "4. File an incident report with TSSA within 24 hours per Ontario Regulation 209/01."
    )

    pdf.section("Earthquake / Seismic Event")
    pdf.body(
        "1. Elevators with seismic shutdown switches will automatically stop at the "
        "nearest landing and open doors after an event - do not override until "
        "a mechanic has inspected the hoistway.\n"
        "2. Inspect guide rails for displacement, counterweight for shifting, "
        "and pit for structural damage before returning to service.\n"
        "3. TSSA must be notified if any structural damage is found."
    )

    pdf.section("TSSA Reporting Requirements")
    pdf.body(
        "Ontario Regulation 209/01, Section 14 requires that the owner report to TSSA "
        "within 24 hours any incident involving:\n"
        "- Injury to a person\n"
        "- Unintended car movement of more than 300 mm\n"
        "- Activation of the governor and safety\n"
        "- Structural failure of any component\n"
        "Use TSSA online portal or call 1-877-682-8772 (after hours: emergency line)."
    )

    pdf.output(str(out))


#  Main 

def main() -> None:
    docs_dir = Path(__file__).parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    pdfs = [
        ("hydraulic_maintenance.pdf",       _hydraulic_maintenance),
        ("traction_troubleshooting.pdf",     _traction_troubleshooting),
        ("safety_code_quick_reference.pdf",  _safety_code),
        ("inspection_types.pdf",             _inspection_types),
        ("common_failure_modes.pdf",         _common_failure_modes),
        ("emergency_response.pdf",           _emergency_response),
    ]

    for filename, fn in pdfs:
        path = docs_dir / filename
        fn(path)
        print(f"  wrote {path} ({path.stat().st_size:,} bytes)")

    print(f"\nAll {len(pdfs)} PDFs written to {docs_dir}")


if __name__ == "__main__":
    main()
