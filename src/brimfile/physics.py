from math import sin, radians
def Brillouin_shift_water(wavelength_nm: float, temperature_C: float, scattering_angle_deg: float) -> float:
    """
    Calculate the Brillouin shift for water at a given temperature and wavelength.

    Args:
        wavelength (float): Wavelength in nanometers.
        temperature (float): Temperature in degrees Celsius. Valid range 20 to 40 °C.
        scattering_angle (float): Scattering angle in degrees.
    Returns:
        float: Brillouin shift in GHz.
    """
    # refractive index of water (dimensionless)
    refractive_index = 1.333
    # Speed of sound in water as a function of temperature (in m/s)
    # obtained by fitting a 4th-order polynomial to experimental data from Supplementary Table 1 of https://doi.org/10.1038/s41566-025-01681-6
    # while assuming a constant refractive index of 1.333 across the temperature range of 20 to 40 °C
    speed_of_sound = 1485.115245 - 6.273078 * temperature_C + 5.308978e-1 * temperature_C**2 + \
                        -1.319485681e-2 * temperature_C**3 + 1.12602896e-4 * temperature_C**4
    # Brillouin shift calculation (in GHz)
    shift_ghz = 2 * speed_of_sound * refractive_index * sin(radians(scattering_angle_deg/2)) / wavelength_nm
    return shift_ghz