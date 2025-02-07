#!/usr/bin/python3
# Øystein Godøy, METNO/FOU, 2021-02-11 
#
import sys
import os
import argparse
import threddsclient
import urllib.request

def traverse_thredds(mystart, dstdir, mydepth, createlist, printscreen):
    print('Traversing:', mystart)
    mylist = []
    for ds in threddsclient.crawl(mystart, depth=mydepth):
        mypath = (ds.url.split('?')[0].replace('catalog.xml','')).replace(mystart.replace('catalog.html',''),'')
        newdstdir = os.path.join(dstdir,mypath)
        if not os.path.exists(newdstdir):
            try:
                os.makedirs(newdstdir)
            except:
                print("Can't create directory for list file or download files")
                return
        file2create = '/'.join([newdstdir,os.path.basename(ds.download_url())])
        if printscreen:
            print(ds.download_url(), file2create)
        mylist.append(ds.download_url())
        if not createlist:
            try:
                urllib.request.urlretrieve(ds.download_url(),file2create)
            except:
                print('Can\'t retrieve:', ds.download_url())
                continue

    if createlist:
        mylistfile = '/'.join([dstdir,'files2download.txt'])
        try:
            print('Creating output file at:', mylistfile)
            myfile = open(mylistfile,'w')
        except:
            print("Can't open output file for list: ", mylistfile)
            return
        for line in mylist:
            print(line, file=myfile)

        myfile.close()

    return

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(
            description='Traverse THREDDS catalogues and extract '+
            'discovery metadata to MMD where ACDD elements are present')
    parser.add_argument('starturl', type=str, 
            help='URL to start traverse')
    parser.add_argument('dstdir', type=str, 
            help='Directory where to put MMD files')
    parser.add_argument('-d', '--depth', type=int, default=3, 
            help='How meny levels below the top level to evaluate')
    parser.add_argument('-l', '--createlist', action='store_true', 
            help='Do not download, only create list of files to download')
    parser.add_argument('-p', '--printscreen', action='store_true', 
            help='Print list of files to download to screen')
    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        sys.exit()
    
    try:
        traverse_thredds(args.starturl, args.dstdir, args.depth, args.createlist, args.printscreen)
    except:
        print('Something went wrong', sys.exc_info()[0])
        sys.exit()
