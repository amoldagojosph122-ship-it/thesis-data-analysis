-- 0014_dem_elevations.sql
-- Provisional collar elevations from a digital elevation model (Copernicus GLO-30). A surveyed collar RL is still
-- absent, so the DEM values are kept in separate PROVISIONAL columns. z_absolute_m stays NULL until an APPROVED
-- elevation source exists.

ALTER TABLE holes ADD COLUMN dem_elevation_m REAL;
ALTER TABLE holes ADD COLUMN dem_status TEXT CHECK (dem_status IS NULL OR dem_status = 'PROVISIONAL');
ALTER TABLE interval_coordinates ADD COLUMN z_dem_absolute_m REAL;

INSERT OR IGNORE INTO elevation_sources (elevation_source_id, source_type, description, vertical_datum, status)
VALUES (2, 'DEM',
        'Copernicus DEM GLO-30 (digital surface model), tile N10 W003; bilinear at collar coordinates; provisional, not a surveyed collar RL',
        'Heights as distributed by the Copernicus DEM (EGM2008 geoid)',
        'PROVISIONAL');
