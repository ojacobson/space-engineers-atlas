#!/usr/bin/env python3

import argparse as ap
import collections as c
import lxml.etree as etree
import math as m
import flask as f
import flask.json as fj

Station = c.namedtuple('Station', ['tag', 'gps'])

def faction_station(tag, station):
    position = station.find('Position')
    x, y, z = (position.get(axis) for axis in ('x', 'y', 'z'))
    return Station(
        tag=tag,
        gps=f"GPS:{tag} Station:{x}:{y}:{z}:",
    )

def faction_gps(faction):
    tag = faction.findtext('Tag')
    stations = faction.xpath('Stations/MyObjectBuilder_Station')
    for station in stations:
        yield faction_station(tag, station)

def dump_station_gps(file):
    tree = etree.parse(file)
    factions = tree.xpath('/MyObjectBuilder_Checkpoint/Factions/Factions/MyObjectBuilder_Faction')
    return [
        entry
        for faction in factions
        for entry in faction_gps(faction)
    ]

def planet_name(planet):
    return planet.findtext('PlanetGenerator')

def planet_gps(planet):
    name = planet_name(planet)

    position = planet.find('PositionAndOrientation/Position')
    x, y, z = (float(position.get(axis)) for axis in ('x', 'y', 'z'))

    maximum_hill_radius = float(planet.findtext('MaximumHillRadius'))

    # Thanks to Digi in the Space Engineers discord for this!
    # <https://discordapp.com/channels/125011928711036928/216219467959500800/700530462350901360>
    octree_size = 2 ** m.ceil(m.log(maximum_hill_radius, 2))

    centre_x, centre_y, centre_z = (axis + octree_size for axis in (x, y, z))

    return f"GPS:{name}:{centre_x}:{centre_y}:{centre_z}:"

Planet = c.namedtuple('Planet', ['name', 'gps'])

def dump_planets_gps(file):
    tree = etree.parse(file)
    planets = tree.xpath(
        '/MyObjectBuilder_Sector/SectorObjects/MyObjectBuilder_EntityBase[@xsi:type = "MyObjectBuilder_Planet"]',
        namespaces={
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }
    )
    return [
        Planet(
            name=planet_name(planet),
            gps=planet_gps(planet)
        )
        for planet in planets
    ]

app = f.Flask(__name__)

@app.route('/stations', methods=['POST'])
def stations():
    stations = dump_station_gps(f.request.stream)
    return fj.jsonify([station._asdict() for station in stations])

@app.route('/planets', methods=['POST'])
def planets():
    planets = dump_planets_gps(f.request.stream)
    return fj.jsonify([planet._asdict() for planet in planets])

@app.route('/')
def ui():
    return app.send_static_file("index.html")
