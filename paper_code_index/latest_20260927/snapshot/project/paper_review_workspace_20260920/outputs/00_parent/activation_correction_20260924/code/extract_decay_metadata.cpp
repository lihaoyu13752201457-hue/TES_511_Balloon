#include <zlib.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#pragma pack(push,1)
struct Event {uint32_t id,za; double time,x,y,z,exc; int32_t primza; uint32_t flags;};
struct Future {uint32_t parent,za; double exc,delay;};
#pragma pack(pop)
const std::vector<std::string> els={"","H","He","Li","Be","B","C","N","O","F","Ne","Na","Mg","Al","Si","P","S","Cl","Ar","K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn","Ga","Ge","As","Se","Br","Kr","Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd","In","Sn","Sb","Te","I","Xe","Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu","Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg","Tl","Pb","Bi","Po","At","Rn","Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm"};
int nuclide(const char *s,double &ex){
 const char *p=s;while(*p&&std::isalpha(*p))++p;
 std::string el(s,p-s);int z=0;
 for(size_t k=1;k<els.size();++k)if(el==els[k]){z=k;break;}
 if(!z||!std::isdigit(*p))return 0;
 int a=std::strtol(p,const_cast<char**>(&p),10);ex=0;
 if(*p=='[')ex=std::strtod(p+1,nullptr);
 return z*1000+a;
}
int main(int argc,char**argv){
 if(argc!=4)return 2;
 gzFile f=gzopen(argv[1],"rb");if(!f)return 3;gzbuffer(f,1<<20);
 std::ofstream o(argv[2],std::ios::binary),q(argv[3],std::ios::binary);
 Event e{};bool active=false;uint64_t count=0,unknown=0,futures=0;
 auto flush=[&](){if(!active)return;if(!(e.flags&1)||!(e.flags&2))throw std::runtime_error("missing INIT/TI");if(!(e.flags&4))++unknown;o.write(reinterpret_cast<char*>(&e),sizeof(e));++count;active=false;};
 char line[131072];
 while(gzgets(f,line,sizeof(line))){
  if(std::strncmp(line,"SE\n",3)==0||std::strcmp(line,"SE\r\n")==0){flush();e=Event{};e.exc=NAN;active=true;}
  else if(active&&std::strncmp(line,"ID ",3)==0)e.id=std::strtoul(line+3,nullptr,10);
  else if(active&&std::strncmp(line,"TI ",3)==0){e.time=std::strtod(line+3,nullptr);e.flags|=2;}
  else if(active&&std::strncmp(line,"IA INIT",7)==0){
   const char*p=line;for(int k=0;k<16;++k){
    if(k==4)e.x=std::strtod(p,nullptr);if(k==5)e.y=std::strtod(p,nullptr);if(k==6)e.z=std::strtod(p,nullptr);if(k==15)e.za=std::strtoul(p,nullptr,10);
    if(k<15){p=std::strchr(p,';');if(!p)throw std::runtime_error("bad INIT");++p;}}
   if(e.flags&1)throw std::runtime_error("multiple INIT");e.flags|=1;
  }else if(active&&std::strncmp(line,"CC HIT ",7)==0&&!(e.flags&4)){
   const char*p=std::strstr(line," prim=");if(p){double ex=0;int za=nuclide(p+6,ex);if(za){e.primza=za;e.exc=ex;e.flags|=4;}}
  }else if(active&&std::strncmp(line,"CC Future decay: ",17)==0){
   Future v{};v.parent=e.id;v.za=nuclide(line+17,v.exc);const char*p=std::strstr(line," at t=");if(!v.za||!p)throw std::runtime_error("bad Future");v.delay=std::strtod(p+6,nullptr);q.write(reinterpret_cast<char*>(&v),sizeof(v));++futures;
  }
 }
 flush();int err=0;gzerror(f,&err);gzclose(f);if(err!=Z_OK&&err!=Z_STREAM_END)return 4;
 std::cout<<"{\"events\":"<<count<<",\"unknown_excitation\":"<<unknown<<",\"future_records\":"<<futures<<",\"event_record_bytes\":"<<sizeof(Event)<<",\"future_record_bytes\":"<<sizeof(Future)<<"}\n";
}
