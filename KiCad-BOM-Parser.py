import xml.etree.ElementTree as ET
import csv

features_to_skip = ['Designator', 'Quantity']

#Check if componants are the same except features
def is_component_equal(component1, component2, features):
    keys1 = component1.keys()
    keys2 = component2.keys()
    for feature in features:
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

#Check if component is in list but ignoring features
def is_component_in_list(component, components_list, features):
    result = {'presence': False, 'position': 0}
    for i, component_from_list in enumerate(components_list):
        if is_component_equal(component,
                              component_from_list,
                              features):
            result['presence'] = True
            result['position'] = i
            return result
    return result

#Load data from KiCad xml file
def extract_components_from_xml(file):
    components = []
    tree = ET.parse(file)
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
    return components

#Building list of unique elements but ignoring features
def find_unique_components(components_list, features):
    unique_components = []
    for component in components:
        result = is_component_in_list(component,
                                      unique_components,
                                      features)
        if result['presence'] == True:
            unique_components[result['position']]['Designator'] += ' ' + component['Designator']
            unique_components[result['position']]['Quantity'] += 1
        else:
            component['Quantity'] = 1
            unique_components.append(component)

    return unique_components

def get_all_feauters(components):
    features = set()
    for component in components:
        for key in component:
            features.add(key)
    return features

def generate_csv(unique_components):
    fieldnames = get_all_feauters(unique_components)
    print fieldnames
    with open('out.csv', 'wb') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_components)
        for component in unique_components:
            print component
            #writer.writerow(component)

components = extract_components_from_xml('vs3000-main-board.xml')
unique_components = find_unique_components(components, features_to_skip)
unique_components = sorted(unique_components, key=lambda k: k['Designator'])
generate_csv(unique_components)
get_all_feauters(unique_components)

#for component in unique_components:
 #   print component

print '....................................SUMMARY....................................'
print 'In:', len(components), 'components found', len(unique_components), 'unique.'
