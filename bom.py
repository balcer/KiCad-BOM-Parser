"""This program converts .xml input file generated by KiCAD into
.csv file of unique components with quantity
"""

from __future__ import print_function

import xml.etree.ElementTree as ET
import csv
import sys
import os
import string
import natsort

def main():

    """Main function of the program."""

    if len(sys.argv) < 2 or sys.argv[1] == '--help':
        print('Usage: python {} KICAD_PROJECT_DIRECTORY'.format(sys.argv[0]))
        sys.exit()
    else:
        path_to_project_directory = sys.argv[1]
        for project_file in os.listdir(path_to_project_directory):
            if project_file.endswith(".xml"):
                xml_file_name = project_file
            elif project_file.endswith(".kicad_pcb"):
                pcb_file_name = project_file

        path_to_xml_file = path_to_project_directory + xml_file_name
        path_to_pcb_file = path_to_project_directory + pcb_file_name
        path_to_csv_file = path_to_project_directory + os.path.splitext(xml_file_name)[0] + ".csv"

    features_to_skip = ['Designator', 'Quantity']

    components_from_xml = extract_components_from_xml(path_to_xml_file)
    components_from_pcb = extract_components_from_pcb(path_to_pcb_file)
    components_merged = merge_components(components_from_xml, components_from_pcb)
    unique_components = find_unique_components(components_merged, features_to_skip)
    generate_csv(unique_components, path_to_csv_file)

def extract_components_from_xml(path_to_file):

    """Load raw data about components from KiCAD xml file."""

    print('Extracting data from {}...'.format(os.path.basename(path_to_file)), end='')

    components = []
    try:
        tree = ET.parse(path_to_file)
    except IOError:
        print('Input file error')
        sys.exit()
    root = tree.getroot()
    for comp in root.iter('comp'):
        component = {'Designator': comp.get('ref'),
                     'Value': comp.find('value').text,
                     'Footprint': comp.find('footprint').text}
        fields = comp.find('fields')
        if fields is not None:
            for field in fields.iter('field'):
                component[field.get('name')] = field.text
        components.append(component)

    print('done.')
    print('Found {} components.'.format(len(components)))

    return components

def extract_components_from_pcb(path_to_file):

    """Load additional data from KiCAD PCB file."""

    print('Extracting data from {}...'.format(os.path.basename(path_to_file)), end='')

    data = []
    with open(path_to_file) as pcb_file:
        for line in pcb_file:
            for word in line.split():
                data.append(word)

    components = []
    designator = ''
    bracket_counter = 0
    smd_counter = 0
    tht_counter = 0
    in_module = False

    for idx, word in enumerate(data):
        if word == '(module':
            bracket_counter = 0
            smd_counter = 0
            tht_counter = 0
            in_module = True
        if in_module is True:
            if word == 'reference':
                designator = data[idx + 1]
            if word == '(pad':
                if data[idx + 2] == 'smd':
                    smd_counter = smd_counter + 1
                if data[idx + 2] == 'thru_hole':
                    tht_counter = tht_counter + 1
            bracket_counter = bracket_counter + word.count('(') - word.count(')')
        if (bracket_counter == 0) and (in_module is True):
            in_module = False
            component = {'Designator': designator,
                         'smd_count': smd_counter,
                         'thru_hole': tht_counter}
            components.append(component)

    print('done.')
    print('Found {} components.'.format(len(components)))

    return components

def merge_components(components_from_xml, components_from_pcb):

    """Checks integrity of both lists and merge them together"""

    print('Merging data from xml and pcb files...', end='')

    if len(components_from_xml) != len(components_from_pcb):
        print('error.')
        sys.exit()

    component_counter = 0

    for component_from_xml in components_from_xml:
        for component_from_pcb in components_from_pcb:
            if component_from_xml['Designator'] == component_from_pcb['Designator']:
                component_counter += 1
                break

    if len(components_from_xml) != component_counter:
        print('error.')
        sys.exit()

    """Adding features from pcb component list to xml component list"""

    for component_from_xml in components_from_xml:
        for component_from_pcb in components_from_pcb:
            if component_from_xml['Designator'] == component_from_pcb['Designator']:
                component_from_xml['SMD pads'] = component_from_pcb['smd_count']
                component_from_xml['THT pads'] = component_from_pcb['thru_hole']

    print('done.')

    return components_from_xml

def is_component_equal(component1, component2, omit_features):

    """Check if components are the same except features in omit_features."""

    keys1 = component1.keys()
    keys2 = component2.keys()
    for feature in omit_features:
        if feature in keys1:
            keys1.remove(feature)
        if feature in keys2:
            keys2.remove(feature)
    if len(keys1) == len(keys2):
        for key in keys1:
            if key in component2 and component1[key] == component2[key]:
                pass
            else:
                return False
        return True
    return False

def is_component_in_list(component, components_list, features):

    """Check if component is in list ignoring features."""

    result = {'presence': False, 'position': 0}
    for i, component_from_list in enumerate(components_list):
        if is_component_equal(component,
                              component_from_list,
                              features):
            result['presence'] = True
            result['position'] = i
            return result
    return result

def find_unique_components(components_list, features):

    """Converts raw components list to list of unique components
    omitting omit_features and adds Quantity according to how many
    components were equal. Additionally build Designator string which
    contains Designators of all equal components separated by space.
    """

    print('Building unique components list...', end='')

    unique_components = []
    for component in components_list:
        result = is_component_in_list(component,
                                      unique_components,
                                      features)
        if result['presence'] is True:
            unique_components[result['position']]['Designator'] += ' ' + component['Designator']
            unique_components[result['position']]['Quantity'] += 1
        else:
            component['Quantity'] = 1
            unique_components.append(component)

    unique_components = sorted(unique_components, key=lambda k: k['Designator'])
    sort_designators(unique_components)

    print('done.')
    print('Found {} unique components.'.format(len(unique_components)))

    return unique_components

def sort_designators(components):

    """Sort Designator string to make it more readable.
    "R1 R3 R2" -> "R1 R2 R3"
    """

    for component in components:
        designators = string.split(component['Designator'])
        sorted_designators = natsort.natsorted(designators)
        component['Designator'] = " ".join(sorted_designators)

def get_all_features(components):

    """Extracts all features from component list."""

    features = set()
    for component in components:
        for key in component:
            features.add(key)
    return features

def generate_csv(unique_components, path_to_file):

    """Generate output csv file."""

    fieldnames = get_all_features(unique_components)
    with open(path_to_file, 'wb') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_components)

    print('Data saved to {}.'.format(os.path.basename(path_to_file)))

if __name__ == "__main__":
    main()
