#include <zlib.h>
#include <string>
#include <sstream>
#include <iostream>
#include <iomanip>
#include <vector>
#include <regex>
#include <cstring>
int main(int argc,char**argv){
 if(argc!=4)return 2;gzFile f=gzopen(argv[1],"rb");if(!f)return 3;gzbuffer(f,1<<20);
 std::string target=argv[2];int za=std::stoi(argv[3]),id=0;double energy=0;bool matched=false,init=false;char line[262144];
 while(gzgets(f,line,sizeof(line))){
  if(std::strncmp(line,"SE",2)==0){if(matched&&init){std::cout<<id<<" "<<std::setprecision(17)<<energy<<"\n";gzclose(f);return 0;}matched=false;init=false;}
  if(std::strncmp(line,"ID ",3)==0)id=std::stoi(line+3);
  if(std::strncmp(line,"CC IP RP ",9)==0){std::istringstream s(line+9);std::string v;double x,y,z,exc;int a;s>>v>>x>>y>>z>>a>>exc;
   if(v.size()>3&&v.substr(v.size()-3)=="_pv")v.resize(v.size()-3);
   std::smatch m;if(std::regex_match(v,m,std::regex("TP_L([0-9]+)_[0-9]+")))v="TES_Pixel_L"+m[1].str();
   if(v==target&&a==za&&exc==0)matched=true;
  }
  if(std::strncmp(line,"IA INIT",7)==0){std::stringstream s(line);std::string a;std::vector<std::string> v;while(std::getline(s,a,';'))v.push_back(a);energy=std::stod(v.back());init=true;}
 }
 if(matched&&init){std::cout<<id<<" "<<std::setprecision(17)<<energy<<"\n";gzclose(f);return 0;}gzclose(f);return 4;
}
