from subprocess import call
import requests
import json
import xml.etree.ElementTree as ET
import re
import sys

parse_tree = []
NS = {'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
      'role': 'http://www.cs.rochester.edu/research/trips/role#',
      'LF': 'http://www.cs.rochester.edu/research/trips/LF#'}

#stores the ontology entries in the format ontology[concept] = [concept, [parents], [related concepts (W:: stuff)]]
#note that ontology contains both concepts and words (ONT::'s and W::'s), for words the '[related concepts]'-list is empty
ontology = {}

#for each entry in ontology (all ONT::'s and W::'s) stores the list of all ancestors
#for words it is concepts to which they are related and their ancestors
supertypes = {}

#recursively obtains the list of ancestors of the given ontology entry and assigns it to supertypes[entry]
def add_supertypes(concept, ontology, supertypes):
        #get all parents
        ancestors = ontology[concept][1]

        #get parents of parents and so on, recursively
        for parent in ontology[concept][1]:
                if(parent not in supertypes.keys()):
                        supertypes = add_supertypes(parent, ontology, supertypes)
                ancestors = ancestors + supertypes[parent]

        #remove duplicates and assign the ontology entry
        supertypes[concept] = list(set(ancestors))
        
        return supertypes

#transforms tokens into the unified format whenever possible, for easier pattern matching
def process_token(token):
        token = token.strip().upper()
        
        #if token is in ontology, just return
        if token in supertypes.keys():
                return token

        #if token is 'xxx/yyy', get the 'yyy' part
        if '/' in token:
                return token.split('/')[1].strip()

        #if the ONT::token or W::token is in the ontology, return the respective concatenation
        if ("W::" + token) in supertypes.keys():
                return "W::" + token
        if ("ONT::" + token) in supertypes.keys():
                return "ONT::" + token

        #if token is in plural form, try to get the standard ontology representation
        if (len(token) > 0 and token[-1] == 'S'):
                token = token[:-1]
                if "ONT::" + token in supertypes.keys():
                        return "ONT::" + token
                elif ("W::" + token) in supertypes.keys():
                        return "W::" + token
        else:
                #if token is a number
                try:
                        int(token)
                        return "ONT::NUMBER"
                except ValueError:                        
                        return token if token != '' else None
        return token if token != '' else None

#parses the TRIPS ontology file and builds custom ontology and supertypes dictionaries
def build_ontology(filename):
        onto_concepts = {}
        onto_words = {}
        onto_all = {}
        supertypes = {}

        #get the entries for 'ONT::' nodes and fill in the concept ontology
        for concept in ET.parse(filename).getroot().findall('concept'):
                onto_concepts[concept.get('name').strip().upper()] = [concept.get('name').strip().upper(),
                                             [parent.text.strip().upper() for parent in concept.findall("relation[@label='inherit']")],
                                             [word.text.strip().upper() for word in concept.findall("relation[@label='word']")]]
                
        #for each 'ONT::' concept, extract all related words ('W::') and fill in the ontology for words
        for concept in onto_concepts.keys():
                for related in onto_concepts[concept][2]:
                        if(related not in onto_words.keys()):
                                onto_words[related] = [related, [concept], []]
                        else: onto_words[related][1].append(concept)
                        
        #merge them together to get a unified ontology
        onto_all = {**onto_concepts, **onto_words}

        #form the supertype ontology
        for concept in onto_all.keys():
                if concept not in supertypes.keys():
                        supertypes = add_supertypes(concept, onto_all, supertypes)
                        
        return (onto_all, supertypes)

#parses the frames.xml and builds the list of frames representations
def build_frames(filename):
        frame_trees = ET.parse(filename).getroot().findall('frame')
        frames = []
        for frame_tree in frame_trees:
                frames.append([frame_tree.get('name')])
                for field in frame_tree.findall('field'):
                        frames[-1].append([field.get('name'),
                                           field.get('action'),                                           
                                           [[y.strip().upper() for y in x.split()] for x in field.get('pattern').split('|')],
                                           int(field.get('weight'))])
        return frames

#parses the file with test cases and build a list of tests
def build_tests(filename):
        tests = []
        with open(filename) as f:
                raw_tests = f.readlines()
        for test in raw_tests:
                tokens = [process_token(token) for token in re.split('[ ,.!?\n]', test)]                
                tests.append([token for token in tokens if token is not None])
        return tests

#performs the pattern matching
#parameters:
#pattern - pattern to be matched
#sentence - the test case
#next - specifies whether we have to match the next token in the pattern with the next token in the sentence
#return value: the list of indices at which pattern's tokens are occuring in the sentence
def pattern_match(pattern, sentence, next):
        ret_val = None
        if(pattern == []):
                return []
        if(pattern[0] == '*'):
                return pattern_match(pattern[1:], sentence, 0)
        indices = sorted([index for index in range(0, len(sentence))
                   if pattern[0] == sentence[index] or (sentence[index] in supertypes.keys() and pattern[0] in supertypes[sentence[index]])])
        if indices is None or indices == []:
                return None
        if next == 1:
                if 0 in indices:
                        indices = [0]
                else:
                        return None               
        for index in indices:
                if ret_val is None:
                        ret_val = pattern_match(pattern[1:], sentence[index + 1:], 1)
                else:
                        break
        return ret_val if ret_val is None else [index] + [x + index + 1 for x in ret_val]

#frame matching for the given test case and frame
def frame_match(frame, sentence):
        #the matching measure
        score = 0
        #the clarification questions if this frame is the best match
        questions = []
        for field in frame[1:]:
                matching_indices = None
                for pattern in field[2]:
                        matching_indices = pattern_match(pattern, sentence, 0)
                        if matching_indices is not None:
                                sentence = [sentence[i] for i in range(0, len(sentence)) if i not in matching_indices]
                                score = score + field[3]
                                break                        
                #if we failed to match any pattern from this field and it requires
                #a qustion to be asked, add that question to the list
                if (matching_indices is None and '?' in field[1]):
                        questions.append(field[1])                                
        return [score, list(set(questions))]

def get_lf(rdf):
    lf = {}
    for node in rdf.findall('rdf:Description', NS):
        dict = {}
        dict['id'] = '#' + node.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}ID')
        dict['indicator'] = node.find('LF:indicator', NS).text
        dict['type'] = node.find('LF:type', NS).text
        if node.find('LF:word', NS) is not None:
            dict['word'] = node.find('LF:word', NS).text
        dict['start'] = node.find('LF:start', NS).text
        roles = []
        for child in node.getchildren():
            if child.tag.startswith('{http://www.cs.rochester.edu/research/trips/role#}'):
                rolename = child.tag.split('}')[1]
                roleref = child.text if child.text is not None else child.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', NS)
                roles.append((rolename, roleref))
        dict['roles'] = roles
        lf[dict['id']] = dict
    return lf

def get_arg_form(lf, rdf_id):
        arg = [rdf_id]
        for key in lf.keys():
                if lf[key]['id'] == rdf_id:
                        for role in lf[key]['roles']:
                                if role[0] == 'MOD':
                                        arg.append(resolve_reference(role[1]))
        return arg

def resolve_reference(rdf_id):
        return rdf_id

def get_formal_query(lf):
        query = []
        relations = []
        global frames        
        isYN = False
        for key in lf.keys():
                if lf[key]['indicator'] == 'SPEECHACT' and ('PUNCTYPE', 'YNQ') in lf[key]['roles']:
                        isYN = True
        for key in lf.keys():
                for frame in frames:
                        if lf[key]['type'] == frame[0]:
                                relations.append([frame[0]])                                
                                for role in lf[key]['roles']:
                                        if role[0] == 'FIGURE' or role[0] == 'GROUND':
                                                relations[-1].append([role[0]] + get_arg_form(lf, role[1]))
        query = []
        for relation in relations:
                query.append([relation[0]])
                for arg in relation[1:]:
                        new_arg = [arg[0]]
                        for token in arg[1:]:
                                new_arg.append(lf[token]['word'])
                        query[-1].append(new_arg)
        return query

                                                
#ontology, supertypes = build_ontology("trips-ont-lex.xml")
#frames = build_frames("frames.xml")
#print (frames[0])
#tests = [line for line in open("tests", "r").readlines()]
#result = requests.get("http://trips.ihmc.us/parser/cgi/parse?input=" + tests[4])
#root = ET.fromstring(result.text)
#lf = get_lf(root.find('utt').find('terms').find('rdf:RDF', NS))

#for key in lf.keys():
#    print (lf[key], '\n')   

#print (get_formal_query(lf))
print ("Running Blender...")
call(["blender", "blocks_world.blend", "--background", "--python", "main.py"])
