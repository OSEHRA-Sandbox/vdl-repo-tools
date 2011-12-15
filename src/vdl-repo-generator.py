from HTMLParser import HTMLParser
import os.path
import re
import glob
import shutil
import argparse

def _get_argument_parser():
    parser = argparse.ArgumentParser()

    # General arguments    
    parser.add_argument('-m', dest='mirror_dir', action='store',
                        help='The path to the site mirror')
    
    parser.add_argument('-o', dest='output_dir', action='store',
                        help='The path to output dir, repo')
    
    usage = "usage: %prog [options]"
    
    return parser

class Document(object):
    def __init__(self, name) :
        self.name = name
        self.file = None

class HTMLVdlFileDocumentNameParser(HTMLParser) : 
    def __init__(self) :
        HTMLParser.__init__(self)  
        self.in_table = False
        self.in_tr = False
        self.td_index = 0
        self.in_a = False
        self.current_doc = None
        self.current_version = None
        self.files = []

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and attrs[1] == ('summary', 'List of documents'):
            self.in_table = True
      
        if self.in_table and tag == 'tr' and len(attrs) == 1 and attrs[0][0] == 'class':
            self.in_tr = True
      
        if self.in_tr and tag == 'td':
            self.td_index += 1              
      
        if self.td_index == 4 and tag == 'a' and len(attrs) == 1 and self.current_doc != None:    
            
            new_doc = Document(self.current_doc.name)
            new_doc.created = self.current_doc.created
            new_doc.modified = self.current_doc.modified
            new_doc.file = attrs[0][1]
            new_doc.version = self.current_version
            self.files.append(new_doc)
          
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        if tag == 'tr':
            self.in_tr = False
            self.td_index = 0
            self.current_doc = None
            
      
      
      
    def handle_data(self, data):    
        
        if not self.in_table:
            match = re.search(r'^Version ([\d]+[.][\d]*.*)',data.strip())
            if match:
                self.current_version = match.group(1)
            
                        
        if self.td_index == 1:
            self.current_doc = Document(data.strip())
        elif self.td_index == 2:
            self.current_doc.created = data.strip()
        elif self.td_index == 3:
            self.current_doc.modified = data.strip()
        
       
    def get_files(self):
        return self.files

class HTMLVdlSectionFileParser(HTMLParser) : 
    def __init__(self, section) :
        HTMLParser.__init__(self)  
        self.in_table = False
        self.in_tr = False
        self.in_td = False
        self.in_a = False
        self.app_number = -1
        self.section = section
        self.app_num_to_name = dict() 
        

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and attrs[1] == ('summary', 'List of applications'):
            self.in_table = True
      
        if self.in_table and tag == 'tr' and len(attrs) == 1 and attrs[0][0] == 'class':
            self.in_tr = True
      
        if self.in_table and self.in_tr and tag == 'td':
            self.in_td = True              
      
        if self.in_td and tag == 'a' and len(attrs) == 1:    
            self.in_a = True
            self.app_number = attrs[0][1]
          
    def handle_endtag(self, tag):
        if tag == 'table':
            in_table = False
        elif tag == 'tr':
            self.in_tr = False
        elif tag == 'td':  
            self.in_td = False
        elif tag == 'a':
            self.in_a = False;      
            
    def handle_data(self, data):    
        if self.in_a:
            self.app_num_to_name[self.app_number] = (self.section, data.strip())
    
    def get_map(self):
        return self.app_num_to_name;

class HTMLVdlSectionNameParser(HTMLParser) : 
    def __init__(self) :
        HTMLParser.__init__(self)  
        self.in_div = False
        self.in_a = False
        self.section = ''
        self.section_map = dict()
         
    def handle_starttag(self, tag, attrs):
        if tag == 'div' and len(attrs) == 1 and attrs[0][1] == 'breadcrumbs':
            self.in_div = True              
      
        if self.in_div and tag == 'a' and len(attrs) == 1:    
            self.in_a = True
            self.section = attrs[0][1]
          
    def handle_endtag(self, tag):
        if tag == 'div':
            self.in_div = False
        elif tag == 'a':
            self.in_a = False;      
            
    def handle_data(self, data):    
        if self.in_div and self.in_a:
            self.section_map[self.section] = data.strip()
    
    def get_map(self):
        return self.section_map

    

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)     

def write_stats(created, modified, dir):
    file = dir + 'info.txt'
    with open(file, 'w') as fp:
        fp.write(created)
        fp.write('\n')
        fp.write(modified)
   

def _get_app_file_to_app_mapping(section_files):
    app_file_to_app_map = dict()
    
    for file in section_files:
        with open(file, 'r') as fp:
            html = fp.read()
        parser = HTMLVdlSectionFileParser(file[file.rindex('/') + 1:])
        parser.feed(html)
        parser.close()
        app_file_to_app_map.update(parser.get_map())
    
    return app_file_to_app_map


def _get_section_mapping(section_file):
    with open(section_file, 'r') as fp:
        html = fp.read()
    section_parser = HTMLVdlSectionNameParser()
    section_parser.feed(html)
    section_parser.close()
    section_map = section_parser.get_map()
    return section_map



def _get_docs(config, app_file_to_app_map, section_map):
    files = glob.glob('%swww.va.gov/vdl/application.asp?appid=*' % config.mirror_dir)
    file_list = []
    for file in files:
        with open(file, 'r') as fp:
            html = fp.read()
        htmlparser = HTMLVdlFileDocumentNameParser()
        htmlparser.feed(html)
        htmlparser.close()
        docs = htmlparser.get_files()
        for doc in docs:
            section, app = app_file_to_app_map[file[file.rindex('/') + 1:]]
            doc.app = app
            doc.section = section_map[section]
        
        file_list.extend(docs)
    
    return file_list

def _get_file_to_doc_mapping(config, app_file_to_app_map, section_map):
    file_list = _get_docs(config, app_file_to_app_map, section_map)
    
    mapping = dict()
    for f in file_list:
        mapping[f.file] = f
    
    return mapping

def _get_long_filename_mapping():
    with open('long_filename_truncations', 'r') as fp:
            truncations = fp.readlines()
    mapping = dict()
    
    for t in truncations:
        parts = t.split('=')
        mapping[parts[0].strip()] = parts[1].strip()
    
    return mapping
            
def _encode(str):
    str = str.replace('/', '%2F')
    str = str.replace('*', '%2A')
    str = str.replace(':', '%3A')
    
    return str

def _convert_newlines(file):
    with open(file, "rb") as fp:
        data = fp.read()
    
    newdata = data.replace("\r\n", "\n")
    
    if newdata != data:
        with open(file, "wb") as fp:
            fp.write(newdata)
           
def _process_docs(config, file_to_doc_map):
    output = config.output_dir    
    long_filename_mapping = _get_long_filename_mapping()
    files = glob.glob('%swww.va.gov/vdl/documents/**/*/*' % config.mirror_dir)
    for f in files:
        
        with open(f, 'r') as fp:
            data = fp.read()
            if data.find('<title>Page Not Found</title>') != -1:
                continue;
        
        parts = f.split('vdl/')
        
        if not parts[1] in file_to_doc_map:
            print parts[1]
            continue
            
        doc = file_to_doc_map[parts[1]]
        dir_postfix = _encode(doc.name)
        file_path = '%s/%s/' % (doc.section, _encode(doc.app))
        #file_path = file_path[file_path.index('/')+1:file_path.rindex('/')+1]
        if doc.version != None:
            file_path += _encode(doc.version) + '/'
        file_path += dir_postfix
        
        if file_path in long_filename_mapping:
            short_path = long_filename_mapping[file_path]
            ensure_dir(output + short_path)
            with open(output + short_path +'/fullname', 'w') as fp:
                fp.write('%s\n' % dir_postfix)
                file_path = short_path
        
        file_path = output + file_path
        
        ensure_dir(file_path)
        write_stats(doc.created, doc.modified, file_path + '/')
        target = file_path + f[f.rindex('/'):]
        shutil.copyfile(f, target)
        
        if target.endswith('.txt'):
            _convert_newlines(target)

def main():
    
    parser = _get_argument_parser()
    config = parser.parse_args()
    
    
    
    section_files = glob.glob('%swww.va.gov/vdl/section.asp?secid=*' % config.mirror_dir)
    
    app_file_to_app_map = _get_app_file_to_app_mapping(section_files)   
    
    # get section file_to_doc_map
    section_map = _get_section_mapping(section_files[0])
    
    file_to_doc_map = _get_file_to_doc_mapping(config, app_file_to_app_map, section_map)

    _process_docs(config, file_to_doc_map)
    
if __name__ == '__main__': 
    main() 
