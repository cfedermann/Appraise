import sys
from os.path import split

def usage():
    return "\n\tcreate_ranking_xml.py <source> <sysA> <sysB> <sysC> <sysD>\n"

if __name__ == "__main__":
    if not len(sys.argv) == 6:
        print usage()
        sys.exit(-1)
    
    source = []
    targets = [[], [], [], []]
    
    with open(sys.argv[1]) as src_file:
        for line in src_file:
            source.append(line.strip())
    
    for k in range(4):
        with open(sys.argv[2+k]) as src_file:
            for line in src_file:
                targets[k].append(line.strip())
    
    assert len(source) == len(targets[0]) == len(targets[1]) \
      == len(targets[2]) == len(targets[3])
    
    print '<doc id="TASK_ID" source_language="SRC_LANG" target_language="TGT_LANG">'
    for k in range(len(source)):
        print '  <sentence id="{0}">'.format(k)
        print '    <source>{0}</source>'.format(source[k])
        print '    <target system="{0}">{1}</target>'.format(split(sys.argv[2])[1], targets[0][k])
        print '    <target system="{0}">{1}</target>'.format(split(sys.argv[3])[1], targets[1][k])
        print '    <target system="{0}">{1}</target>'.format(split(sys.argv[4])[1], targets[2][k])
        print '    <target system="{0}">{1}</target>'.format(split(sys.argv[5])[1], targets[3][k])
        print '  </sentence>'
    print '</doc>'

    