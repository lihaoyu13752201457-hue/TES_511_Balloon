#include <zlib.h>
#include <string>
#include <sstream>
#include <fstream>
#include <iostream>
#include <map>
#include <vector>
#include <cstring>
struct Meta{std::string first,last;};
std::string value(const std::string&s,const std::string&key){auto i=s.find(key);if(i==std::string::npos)return "";i+=key.size();auto j=s.find(' ',i);return s.substr(i,j-i);}
int main(int argc,char**argv){if(argc!=3)return 2;gzFile f=gzopen(argv[1],"rb"),o=gzopen(argv[2],"wb4");if(!f||!o)return 3;gzbuffer(f,1<<20);gzbuffer(o,1<<20);char line[1048576];std::string ident,head,init;std::vector<std::string> ia,rp,ht;std::map<int,Meta> meta;bool deca=false,started=false;long nev=0,nout=0,nrp=0;auto write=[&](const std::string&s){gzwrite(o,s.data(),s.size());};auto flush=[&](){if(!started)return;if(deca||!rp.empty()){write("SE\n"+ident);write(init);for(auto&s:rp)write(s);if(deca){for(auto&s:ia)write(s);for(auto&kv:meta){write(kv.second.first);if(kv.second.last!=kv.second.first)write(kv.second.last);}for(auto&s:ht)write(s);}nout++;nrp+=rp.size();}ident.clear();init.clear();ia.clear();rp.clear();ht.clear();meta.clear();deca=false;};while(gzgets(f,line,sizeof(line))){
 if(std::strncmp(line,"SE\n",3)==0){if(!started)write(head);flush();started=true;nev++;continue;}
 if(!started){head+=line;continue;}
 if(std::strncmp(line,"ID ",3)==0){ident=line;continue;}
 if(std::strncmp(line,"IA INIT",7)==0){init=line;continue;}
 if(std::strncmp(line,"IA ",3)==0){ia.emplace_back(line);if(std::strncmp(line,"IA DECA",7)==0)deca=true;continue;}
 if(std::strncmp(line,"CC IP RP ",9)==0){rp.emplace_back(line);continue;}
 if(std::strncmp(line,"HTsim ",6)==0){ht.emplace_back(line);continue;}
 if(std::strncmp(line,"CC HIT ",7)==0){std::string s=line;auto sec=value(s," sec=");bool ion=false;for(char c:sec)if(c>='0'&&c<='9')ion=true;if(ion||s.find(" cproc=RadioactiveDecay")!=std::string::npos){int tid=std::stoi(value(s," tid="));auto &m=meta[tid];if(m.first.empty())m.first=s;m.last=s;}}
 }
 flush();write("EN\n");gzclose(f);gzclose(o);std::cout<<nev<<" "<<nout<<" "<<nrp<<"\n";return 0;}
