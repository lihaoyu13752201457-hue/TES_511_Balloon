#include <iostream>
#include <iomanip>
#include <cmath>
#include <string>
#include <cstdlib>
using namespace std;
double getrcpp(double,double);
double getdcpp(double,double);
double get511fluxCpp(double,double,double);
double getSpecCpp(int,double,double,double,double,double);
double getSpecAngFinalCpp(int,double,double,double,double,double,double);
int main(int argc,char**argv){
 if(argc!=5)return 2;
 double lat=stod(argv[1]),lon=stod(argv[2]),h=stod(argv[3]),w=stod(argv[4]);
 double r=getrcpp(lat,lon),d=getdcpp(h,lat);
 cout<<setprecision(17)<<"META,"<<lat<<","<<lon<<","<<h<<","<<w<<","<<r<<","<<d<<","<<get511fluxCpp(w,r,d)<<"\n";
 cout<<"family,energy_keV_total,flux_cm2_s_keV,flux_20bin_cm2_s_keV\n";
 string family;double E;
 while(cin>>family>>E){
   int ip=-1,ia=1,ang=0;
   if(family=="gamma"){ip=33;ang=6;}else if(family=="p"){ip=1;ang=2;}
   else if(family=="alpha"){ip=2;ia=4;ang=3;}else if(family=="n"){ip=0;ang=1;}
   else if(family=="eminus"){ip=31;ang=5;}else if(family=="eplus"){ip=32;ang=5;}
   else if(family=="muplus"){ip=29;ang=4;}else if(family=="muminus"){ip=30;ang=4;}else return 3;
   double e=E/1000./ia;
   double y=getSpecCpp(ip,w,r,d,e,10.)/1000./ia;
   double norm=0;
   for(int j=0;j<20;j++)norm+=2*acos(-1.)*.1*getSpecAngFinalCpp(ang,w,r,d,e,10.,-.95+.1*j);
   if(!isfinite(y)||y<0||!isfinite(norm)||norm<0){cerr<<family<<" "<<E<<" invalid\n";return 4;}
   cout<<family<<","<<E<<","<<y<<","<<y*norm<<"\n";
 }
 return 0;
}
