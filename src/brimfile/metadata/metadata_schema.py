from enum import Enum
from typing import TypeAlias
from dataclasses import dataclass

__docformat__ = "google"


class MetadataEnum(str, Enum):
    """Base enum type for metadata fields that have controlled vocabularies."""

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"] | Enum
MetadataValue: TypeAlias = JSONScalar | MetadataEnum

@dataclass(frozen=True, slots=True)
class MetadataField:
    """Schema definition for one metadata field.

    Attributes:
        name: Canonical metadata key used in file storage.
        python_type: Expected Python type for primitive validation.
        required: Whether the field is mandatory for the metadata section.
        units_required: Whether a units suffix/value is required for this field.
        enum_type: Optional enum class used for controlled vocabularies.
        description: Optional human-readable field description.
    """

    name: str
    python_type: type
    required: bool
    units_required: bool = False
    enum_type: type[MetadataEnum] | None = None
    description: str = ""

class Type(Enum):
    Experiment = 'Experiment'
    Optics = 'Optics'
    Brillouin = 'Brillouin'
    Acquisition = 'Acquisition'
    Spectrometer = 'Spectrometer'


class ImmersionMedium(MetadataEnum):
    other = 'other'
    air = 'air'
    water = 'water'
    oil = 'oil'


class SignalType(MetadataEnum):
    other = 'other'
    spontaneous = 'spontaneous'
    stimulated = 'stimulated'
    time_resolved = 'time_resolved'


class PhononsMeasured(MetadataEnum):
    other = 'other'
    longitudinal = 'longitudinal-like'
    transverse = 'transverse-like'
    longitudinal_Transverse = 'longitudinal-transverse-like'


class PolarizationProbedAnalyzed(MetadataEnum):
    other = 'other'
    VH = 'VH'
    HV = 'HV'
    HH = 'HH'
    VV = 'VV'
    V_Unpolarized = 'V-unpolarized'
    Circular_Circular = 'circular-circular'


class ScanningStrategy(MetadataEnum):
    other = 'other'
    point_scanning = 'point_scanning'
    line_scanning = 'line_scanning'
    light_sheet = 'light_sheet'
    time_resolved = 'time_resolved'


class SpectrometerType(MetadataEnum):
    other = 'other'
    VIPA = 'VIPA'
    FP = 'Fabry_Perot'
    stimulated = 'stimulated'
    heterodyne = 'heterodyne'
    time_domain = 'time_domain'
    impulsive = 'impulsive'


class DetectorType(MetadataEnum):
    other = 'other'
    EMCCD = 'EMCCD'
    CCD = 'CCD'
    sCMOS = 'sCMOS'
    PMT = 'PMT'
    balanced = 'balanced'
    single_PD = 'single_PD'
    single_APD = 'single_APD'


METADATA_SCHEMA: dict[Type, tuple[MetadataField, ...]] = {
    Type.Experiment: (
        MetadataField('Datetime', str, required=False, description="[ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) datetime when the experiment was started"),
        MetadataField('Temperature', float, required=False, units_required=True, description="the temperature measured as close as possible to the sample"),
        MetadataField('Temperature_uncertainty', float, required=False, units_required=True, description=""),
        MetadataField('Sample', str, required=False, description="description of the sample being imaged"),
        MetadataField('Info', str, required=False, description="any additional description that the user can input to describe the experiment"),
    ),
    Type.Optics: (
        MetadataField('Wavelength', float, required=True, units_required=True, description="wavelength of the laser used for the measurements"),
        MetadataField('Power', float, required=True, units_required=True, description="total optical power on the sample"),
        MetadataField('Resolution_x', float, required=True, units_required=True, description=""),
        MetadataField('Resolution_y', float, required=True, units_required=True, description=""),
        MetadataField('Resolution_z', float, required=True, units_required=True, description=""),
        MetadataField('Lens_NA', float, required=True, description="the numerical aperture of the lens that is used for imaging (detection)"),
        MetadataField('Lens_NA_illum', float, required=False, description="the numerical aperture of the lens that is used for illumination (if different from detection)"),
        MetadataField('Immersion_medium', str, required=True, enum_type=ImmersionMedium, description="the immersion medium used for the objective lens"),
        MetadataField('Objective_model', str, required=False, description="the description of the objective lens being used, including the manufacturer and magnification"),
        MetadataField('Laser_model', str, required=False, description=""),
    ),
    Type.Brillouin: (
        MetadataField('Signal_type', str, required=True, enum_type=SignalType, description=""),
        MetadataField('Scattering_angle', float, required=True, units_required=True, description="the average scattering angle (i.e. between the optical axes of the illumination and detection); 180deg corresponds to backscattering"),
        MetadataField('Phonons_measured', str, required=True, enum_type=PhononsMeasured, description=""),
        MetadataField(
            'Polarization_probed_analyzed',
            str,
            required=True,
            enum_type=PolarizationProbedAnalyzed,
            description=""
        ),
        MetadataField('Shift_precision', float, required=True, units_required=True, description=""),
        MetadataField('Width_precision', float, required=True, units_required=True, description=""),
    ),
    Type.Acquisition: (
        MetadataField('Scanning_strategy', str, required=True, enum_type=ScanningStrategy, description=""),
        MetadataField('Acquisition_time', float, required=True, units_required=True, description="the time that takes to acquire a single ‘unit’, which is different depending on the scanning strategy (i.e. point, line, plane, A-line, etc.)"),
    ),
    Type.Spectrometer: (
        MetadataField('Type', str, required=True, enum_type=SpectrometerType, description=""),
        MetadataField('Resolution', float, required=True, units_required=True, description=""),
        MetadataField('Detector_type', str, required=False, enum_type=DetectorType, description=""),
        MetadataField('Detector_model', str, required=False, description=""),
        MetadataField('Additional_filter', str, required=False, description="description of any additional filter present in the spectrometer (e.g. vapor cell, Lyot stop, etc..)"),
        MetadataField('Confocal_pinhole_diameter', float, required=False, units_required=True, description=""),
    ),
}