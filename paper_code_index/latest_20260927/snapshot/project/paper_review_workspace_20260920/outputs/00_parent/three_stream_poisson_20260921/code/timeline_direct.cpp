// Full marked Poisson timeline. No signal-conditioned sampling.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
template<class T> vector<T> readbin(string p){ifstream f(p,ios::binary|ios::ate);if(!f)throw runtime_error(p);size_t n=f.tellg();if(n%sizeof(T))throw runtime_error("shape");vector<T> a(n/sizeof(T));f.seekg(0);f.read((char*)a.data(),n);return a;}
struct Record {float plastic,bgo;uint16_t hits;uint8_t flags,stream;};
static_assert(sizeof(Record)==12);
int main(int argc,char**argv){
 if(argc!=8 && argc!=9)throw runtime_error("directory node T seed Nbackground output tau");
 string dir=argv[1],node=argv[2],out=argv[6];double T=stod(argv[3]),tau=stod(argv[7]);uint64_t seed=stoull(argv[4]);uint32_t nb=stoul(argv[5]);
 int hotN=argc==9?stoi(argv[8]):0;string prefix=hotN?"compact_":"";
 auto rec=readbin<Record>(dir+"/"+prefix+"records.bin");auto w=readbin<double>(dir+"/"+prefix+"weights_"+node+".bin");if(w.size()!=rec.size())throw runtime_error("length");
 double rate=0;array<double,3> rates{};for(size_t i=0;i<w.size();++i){rate+=w[i];rates[rec[i].stream]+=w[i];}
 // Walker alias sampling reproduces each retained event's physical rate weight.
 double hotRate=0;vector<double> hotCDF;for(int k=0;k<hotN;++k){hotRate+=w[k];hotCDF.push_back(hotRate/rate);w[k]=0;}double coldRate=rate-hotRate;
 size_t n=w.size();vector<uint32_t> alias(n),small,large;small.reserve(n);large.reserve(n);
 for(size_t i=0;i<n;++i){w[i]*=n/coldRate;if(w[i]<1)small.push_back(i);else large.push_back(i);}
 while(!small.empty()&&!large.empty()){auto s=small.back();small.pop_back();auto l=large.back();large.pop_back();alias[s]=l;w[l]-=1-w[s];if(w[l]<1)small.push_back(l);else large.push_back(l);}
 for(auto i:small)w[i]=1;for(auto i:large)w[i]=1;small.clear();small.shrink_to_fit();large.clear();large.shrink_to_fit();
 mt19937_64 rng(seed);auto u=[&](){return ((rng()>>11)+0.5)*0x1.0p-53;};
 ofstream groups(out+".groups",ios::binary);array<uint64_t,3> arrivals{};array<uint64_t,3> singles{};uint64_t ng=0,nmulti=0,nemit=0,nsiggroup=0;double t=0,last=0;vector<uint32_t> ids;vector<double> ts;double ep=0,eb=0;bool tes=false,sig=false;
 auto flush=[&](){if(ids.empty())return;ng++;nmulti+=ids.size()>1;nsiggroup+=sig;
  if(!sig&&ids.size()==1){auto f=rec[ids[0]].flags;singles[0]+=bool(f&1);singles[1]+=bool(f&2);singles[2]+=bool(f&4);}
  if(sig || (ids.size()>1&&tes&&eb<50)){uint32_t k=ids.size();groups.write((char*)&ng,8);groups.write((char*)&k,4);for(size_t j=0;j<ids.size();++j){groups.write((char*)&ids[j],4);groups.write((char*)&ts[j],8);}nemit++;}
  ids.clear();ts.clear();ep=eb=0;tes=sig=false;
 };
 auto started=chrono::steady_clock::now();
 while(true){double gap=-log(u())/rate;t+=gap;if(t>T)break;if(!ids.empty()&&gap>tau)flush();
  double mark=u();uint32_t ix=0;bool hot=false;for(int k=0;k<hotN;++k){if(mark<hotCDF[k]){ix=k;hot=true;break;}}
  if(!hot){double draw=(mark-hotRate/rate)/(coldRate/rate)*n;ix=min((uint32_t)draw,(uint32_t)n-1);if(draw-ix>=w[ix])ix=alias[ix];}
  auto r=rec[ix];arrivals[r.stream]++;ids.push_back(ix);ts.push_back(t);ep+=r.plastic;eb+=r.bgo;tes|=r.hits>0;sig|=ix>=nb;last=t;
 }
 flush();groups.close();double elapsed=chrono::duration<double>(chrono::steady_clock::now()-started).count();
 ofstream j(out+".json");j.precision(17);j<<"{\"T\":"<<T<<",\"tau\":"<<tau<<",\"seed\":"<<seed<<",\"rate\":"<<rate<<",\"rates\":["<<rates[0]<<","<<rates[1]<<","<<rates[2]<<"],\"arrivals\":["<<arrivals[0]<<","<<arrivals[1]<<","<<arrivals[2]<<"],\"groups\":"<<ng<<",\"multi_groups\":"<<nmulti<<",\"signal_groups\":"<<nsiggroup<<",\"emitted_groups\":"<<nemit<<",\"background_singleton_counts\":["<<singles[0]<<","<<singles[1]<<","<<singles[2]<<"],\"last_time\":"<<last<<",\"elapsed_s\":"<<elapsed<<"}\n";
 cerr<<out<<" COMPLETE "<<elapsed<<"s; signals="<<arrivals[2]<<" groups="<<nemit<<endl;
}
