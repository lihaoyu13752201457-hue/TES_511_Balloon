// Every arrival is generated on the full three-stream Poisson axis.
// Detailed shield-only marks are materialized only when their group contains
// TES or signal records; groups without either have identically zero readout.
// This optimization treats prompt/delayed TES events and signal alike and does
// not replace any signal record or sample signal-conditioned arrival times.
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
template<class T> vector<T> readbin(string p){ifstream f(p,ios::binary|ios::ate);if(!f)throw runtime_error(p);size_t n=f.tellg();if(n%sizeof(T))throw runtime_error("shape");vector<T>a(n/sizeof(T));f.seekg(0);f.read((char*)a.data(),n);return a;}
struct Record {float plastic,bgo;uint16_t hits;uint8_t flags,stream;};static_assert(sizeof(Record)==12);
struct Alias {vector<uint32_t> ids,other;vector<double> p;double rate=0;
 void build(){size_t n=p.size();other.resize(n);vector<uint32_t> small,large;for(double w:p)rate+=w;if(rate==0)return;for(size_t i=0;i<n;++i){p[i]*=n/rate;(p[i]<1?small:large).push_back(i);}while(!small.empty()&&!large.empty()){auto s=small.back();small.pop_back();auto l=large.back();large.pop_back();other[s]=l;p[l]-=1-p[s];(p[l]<1?small:large).push_back(l);}for(auto i:small)p[i]=1;for(auto i:large)p[i]=1;}
 uint32_t draw(double u){double x=u*p.size();uint32_t i=min((uint32_t)x,(uint32_t)p.size()-1);return ids[x-i<p[i]?i:other[i]];}
};
int main(int argc,char**argv){if(argc!=8&&argc!=9)throw runtime_error("args");string dir=argv[1],node=argv[2],out=argv[6],prefix=argc==9?"compact_":"";double T=stod(argv[3]),tau=stod(argv[7]);uint64_t seed=stoull(argv[4]);uint32_t nb=stoul(argv[5]);
 auto rec=readbin<Record>(dir+"/"+prefix+"records.bin");auto weights=readbin<double>(dir+"/"+prefix+"weights_"+node+".bin");array<Alias,5> samplers;array<double,3> rates{};double total=0;
 for(uint32_t i=0;i<rec.size();++i){auto r=rec[i];double w=weights[i];if(w<=0)continue;int cls=r.stream==2?4:r.stream*2+bool(r.hits);if(!r.hits&&r.flags)throw runtime_error("zero-TES selected event");samplers[cls].ids.push_back(i);samplers[cls].p.push_back(w);rates[r.stream]+=w;total+=w;}
 weights.clear();weights.shrink_to_fit();total=0;for(auto &a:samplers){a.build();total+=a.rate;}rates={samplers[0].rate+samplers[1].rate,samplers[2].rate+samplers[3].rate,samplers[4].rate};array<double,5> cdf{};for(int k=0;k<5;++k)cdf[k]=(k?cdf[k-1]:0)+samplers[k].rate/total;cdf[4]=1;
 mt19937_64 rng(seed);auto u=[&](){return ((rng()>>11)+0.5)*0x1.0p-53;};
 ofstream groups(out+".groups",ios::binary);array<uint64_t,3> arrivals{},singles{};uint64_t ng=0,nmulti=0,nemit=0,nsig=0,single_active=0;vector<uint32_t>ids;vector<double>ts;bool tes=false,sig=false;double t=0,last=0;
 auto flush=[&](){if(ids.empty())return;ng++;nmulti+=ids.size()>1;nsig+=sig;
  if(tes||sig){double eb=0;for(auto &ix:ids){if(ix>=UINT32_MAX-4)ix=samplers[UINT32_MAX-ix].draw(u());eb+=rec[ix].bgo;}
   if(!sig&&ids.size()==1){auto f=rec[ids[0]].flags;singles[0]+=bool(f&1);singles[1]+=bool(f&2);singles[2]+=bool(f&4);single_active+=bool(f&8);}
   if(sig||ids.size()>1){uint32_t n=ids.size();groups.write((char*)&ng,8);groups.write((char*)&n,4);for(size_t j=0;j<ids.size();++j){groups.write((char*)&ids[j],4);groups.write((char*)&ts[j],8);}nemit++;}
  }
  ids.clear();ts.clear();tes=sig=false;
 };
 auto start=chrono::steady_clock::now();
 while(true){double gap=-log(u())/total;t+=gap;if(t>T)break;if(!ids.empty()&&gap>tau)flush();double mark=u();int cls=0;while(cls<4&&mark>=cdf[cls])++cls;int stream=cls==4?2:cls/2;arrivals[stream]++;bool signal=cls==4,hasTES=cls==1||cls==3;uint32_t ix;
  if(signal||hasTES){double lower=cls?cdf[cls-1]:0;ix=samplers[cls].draw((mark-lower)/(cdf[cls]-lower));}else ix=UINT32_MAX-cls;
  ids.push_back(ix);ts.push_back(t);tes|=hasTES;sig|=signal;last=t;
 }
 flush();groups.close();double elapsed=chrono::duration<double>(chrono::steady_clock::now()-start).count();ofstream j(out+".json");j.precision(17);j<<"{\"sampler\":\"full_arrivals_deferred_shield_marks\",\"T\":"<<T<<",\"tau\":"<<tau<<",\"seed\":"<<seed<<",\"rate\":"<<total<<",\"rates\":["<<rates[0]<<","<<rates[1]<<","<<rates[2]<<"],\"arrivals\":["<<arrivals[0]<<","<<arrivals[1]<<","<<arrivals[2]<<"],\"groups\":"<<ng<<",\"multi_groups\":"<<nmulti<<",\"signal_groups\":"<<nsig<<",\"emitted_groups\":"<<nemit<<",\"background_singleton_counts\":["<<singles[0]<<","<<singles[1]<<","<<singles[2]<<"],\"background_singleton_active_count\":"<<single_active<<",\"last_time\":"<<last<<",\"elapsed_s\":"<<elapsed<<"}\n";cerr<<out<<" COMPLETE "<<elapsed<<"s; signals="<<arrivals[2]<<" groups="<<nemit<<endl;
}
