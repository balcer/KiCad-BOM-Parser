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
        print('Usage: python {} [FILE]'.format(sys.argv[0]))
        sys.exit()
    else:
        xml_input_file_name = sys.argv[1]
        pcb_input_file_name = os.path.splitext(os.path.basename(sys.argv[1]))[0] + ".kicad_pcb"
        output_file_name = os.path.splitext(os.path.basename(sys.argv[1]))[0] + ".csv"

    features_to_skip = ['Designator', 'Quantity']

    components_from_xml = extract_components_from_xml(xml_input_file_name)
    components_from_pcb = extract_data_from_pcb_file(pcb_input_file_name)
    unique_components = find_unique_components(components_from_xml, features_to_skip)
    sort_designators(unique_components)
    generate_csv(unique_components, output_file_name)

def extract_components_from_xml(file_name):

    """Load raw data about components from KiCad xml file."""

    print('Extractiong data from {}...'.format(file_name), end='')

    components = []
    try:
        tree = ET.parse(file_name)
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
    print('Found {} components. Features found:'.format(len(components)))

    for key in components[0].keys():
        print(key)

    return components

def extract_data_from_pcb_file(file_name):

    """Load aditional data from KiCad PCB file."""

    print('Extractiong data from {}...'.format(file_name), end='')

    data = []
    with open(file_name) as pcb_file:
        for line in pcb_file:
            for word in line.split():
                data.append(word)

    reference_detected = 0
    components = []

    thru_hole_count = 0
    smd_count = 0
    designator = ''

    for word in data:
        if reference_detected == 1:
            designator = word
            reference_detected = 0
        if word == 'reference':
            component = {'Designator': designator,
                         'smd_count': smd_count,
                         'thru_hole': thru_hole_count}
            components.append(component)
            reference_detected = 1
            thru_hole_count = 0
            smd_count = 0
        if word == 'smd':
            smd_count += 1
        if word == 'thru_hole':
            thru_hole_count += 1
    components.pop(0)

    print('done.')
    print('Found {} components.'.format(len(components)))

    return components

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
    components were equal. Aditionaly build Designator string which
    contains Designators of all equal components separated by space.
    """

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
    return unique_components

def sort_designators(components):

    """Sort Designator string to make it more readible.
    "R1 R3 R2" -> "R1 R2 R3"
    """

    for component in components:
        designators = string.split(component['Designator'])
        sorted_designators = natsort.natsorted(designators)
        component['Designator'] = " ".join(sorted_designators)

def get_all_feauters(components):

    """Extracts all features from component list."""

    features = set()
    for component in components:
        for key in component:
            features.add(key)
    return features

def generate_csv(unique_components, file_name):

    """Generate output csv file."""

    fieldnames = get_all_feauters(unique_components)
    with open(file_name, 'wb') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_components)

if __name__ == "__main__":
    main()
