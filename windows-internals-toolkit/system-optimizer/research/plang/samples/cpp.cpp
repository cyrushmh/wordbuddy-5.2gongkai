#include <iostream>
#include <vector>
#include <map>
#include <fstream>
#include <thread>
#include <mutex>
#include <algorithm>
#include <numeric>
#include <stdexcept>

static int fact(int k){ return k<=1?1:k*fact(k-1); }

int main(){
    std::cout << "LANG=C++" << std::endl;
    int x=42; std::string s="hi"; bool b=true; std::nullptr_t n=nullptr;
    std::cout << "LITERALS=" << x << "," << s << "," << b << "," << 0 << std::endl;
    std::cout << "OPS=" << 7*6 + (int)s.length() << std::endl;
    int acc=0; for(int i=1;i<6;i++) acc+=i;
    std::cout << "CONTROL=" << acc << std::endl;
    std::cout << "FUNC=" << fact(5) << std::endl;
    std::vector<int> arr{1,2,3}; std::map<std::string,int> d{{"a",1}};
    std::cout << "DATA=" << arr.size() << "," << d["a"] << std::endl;
    { std::ofstream f("/tmp/plang_cpp.txt"); f << "io"; }
    { std::ifstream f("/tmp/plang_cpp.txt"); }
    std::remove("/tmp/plang_cpp.txt");
    std::cout << "IO=ok" << std::endl;
    try { throw std::runtime_error("x"); }
    catch(const std::exception& e){ std::cout << "ERROR=std::exception" << std::endl; }
    std::vector<std::thread> ts; std::mutex mu; std::vector<int> res;
    for(int i=0;i<4;i++) ts.emplace_back([i,&mu,&res](){
        std::lock_guard<std::mutex> g(mu); res.push_back(i*i); });
    for(auto& t : ts) t.join();
    std::sort(res.begin(), res.end());
    std::cout << "CONCURRENCY=";
    for(size_t i=0;i<res.size();i++) std::cout << res[i] << (i+1<res.size()?",":"");
    std::cout << std::endl;
    return 0;
}
