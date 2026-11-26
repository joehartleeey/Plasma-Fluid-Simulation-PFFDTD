from skyfield.api import load, EarthSatellite, wgs84
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import json
from ppigrf import ppigrf
import statistics

# -- load sat --
orbit_data = "inputs/orbits/iss.json"

with load.open(orbit_data) as f:
    data = json.load(f)

ts = load.timescale()
satellite = EarthSatellite.from_omm(ts, data[0])
print('Loaded', satellite.name)

# -- consts --
START_TIME = dt.datetime.now(dt.timezone.utc)
ORBIT_PERIOD_SEC = 24 * 60 * 60
DT = 20

seconds = np.arange(0, ORBIT_PERIOD_SEC, DT)
t = ts.tt(START_TIME.year, START_TIME.month, START_TIME.day,
          START_TIME.hour, START_TIME.minute, seconds)

datetimes = [(START_TIME + dt.timedelta(seconds=float(s))).replace(tzinfo=None) for s in seconds]

# -- geodetic positions along one orbit --
geo = satellite.at(t)
pos = wgs84.geographic_position_of(geo)

lon = pos.longitude.degrees
lat = pos.latitude.degrees
hkm = pos.elevation.km

lon_igrf = ((lon + 180) % 360) - 180

print('Sampling IGRF at', lon_igrf.size, 'points ...')
Be, Bn, Bu = ppigrf.igrf(lon_igrf, lat, hkm, datetimes)
Be, Bn, Bu = np.diagonal(Be).copy(), np.diagonal(Bn).copy(), np.diagonal(Bu).copy()

# Total intensity (nT) and unit vector in ENU
F = np.sqrt(Be**2 + Bn**2 + Bu**2)
Bhat_enu = np.stack([Be / F, Bn / F, Bu / F], axis=-1)   # (N, 3)

incl = np.degrees(np.arctan2(np.sqrt(Be**2 + Bn**2), Bu))
decl = np.degrees(np.arctan2(Be, Bn))

# ------------------------------------------------------------------
# ENU -> ECEF unit vectors (for plasma simulations)
# ------------------------------------------------------------------
def enu_to_ecef(lons, lats, e, n, u):
    lon = np.radians(lons)
    lat = np.radians(lats)
    sl, cl = np.sin(lon), np.cos(lon)
    sp, cp = np.sin(lat), np.cos(lat)

    e_hat = np.stack([-sl, cl, np.zeros_like(lon)], axis=-1)
    n_hat = np.stack([-sp * cl, -sp * sl, cp], axis=-1)
    u_hat = np.stack([cp * cl, cp * sl, sp], axis=-1)

    return e[..., None] * e_hat + n[..., None] * n_hat + u[..., None] * u_hat

Bhat_ecef = enu_to_ecef(lon_igrf, lat, Bhat_enu[..., 0], Bhat_enu[..., 1], Bhat_enu[..., 2])

# ------------------------------------------------------------------
# Plot 1: ground track map coloured by |B|, with horizontal arrows
# ------------------------------------------------------------------
fig = plt.figure(figsize=(25, 10))
ax = plt.axes(projection=ccrs.Robinson())
ax.set_global()
ax.set_aspect('auto')
ax.coastlines()
ax.gridlines(linewidth=0.5, linestyle="--")

step = 4  # subsample arrows so they stay readable

# split the track where it crosses the antimeridian
mask = np.abs(np.diff(lon)) < 180
segs = np.where(~mask)[0]
start = 0
for end in np.r_[segs, len(lon) - 1]:
    ax.plot(lon[start:end + 1], lat[start:end + 1], transform=ccrs.PlateCarree(), alpha=0.4, color='gray')
    start = end + 1

im = ax.scatter(lon_igrf, lat, c=F, s=6, cmap='viridis', transform=ccrs.PlateCarree())
q = ax.quiver(lon_igrf[::step], lat[::step], Bhat_enu[::step, 0], Bhat_enu[::step, 1],
              scale=30, width=0.003, color='crimson',
              transform=ccrs.PlateCarree())
plt.colorbar(im, ax=ax, label='|B| (nT)', shrink=0.7)
ax.set_title("ISS Ground Track with IGRF Magnetic Field (horizontal ENU components)")

# ------------------------------------------------------------------
# Plot 2: time series of |B| and inclination
# ------------------------------------------------------------------
fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
tmin = seconds / 60.0

ax1.plot(tmin, F, color='tab:blue')
ax1.set_ylabel('|B| (nT)')
ax1.set_title('IGRF Field Along ISS Track')
ax1.grid(alpha=0.3)

ax2.plot(tmin, incl, color='tab:red')
ax2.axhline(0, color='k', linewidth=0.5)
ax2.set_xlabel('Time into orbit (min)')
ax2.set_ylabel('Inclination (deg)')
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.show()

print("Max |B|: ", max(F), " nT")
print("Min |B|: ", min(F), " nT")
print("Median |B|: ", statistics.median(F), " nT")