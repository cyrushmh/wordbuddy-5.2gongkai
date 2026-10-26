import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public class Main {
    static int fact(int k){ return k<=1?1:k*fact(k-1); }
    public static void main(String[] a) throws Exception {
        System.out.println("LANG=Java");
        int x=42; String s="hi"; boolean b=true; Object n=null;
        System.out.println("LITERALS="+x+","+s+","+b+","+n);
        System.out.println("OPS="+(7*6+"abc".length()));
        int acc=0; for(int i=1;i<6;i++) acc+=i;
        System.out.println("CONTROL="+acc);
        System.out.println("FUNC="+fact(5));
        List<Integer> arr=Arrays.asList(1,2,3);
        Map<String,Integer> d=new HashMap<>(); d.put("a",1);
        System.out.println("DATA="+arr.size()+","+d.get("a"));
        Path p=Files.createTempFile("plang","txt");
        Files.write(p,"io".getBytes()); Files.readAllBytes(p); Files.delete(p);
        System.out.println("IO=ok");
        try { Files.readAllBytes(Paths.get("/nonexistent/plang")); }
        catch(IOException e){ System.out.println("ERROR="+e.getClass().getSimpleName()); }
        ExecutorService ex=Executors.newFixedThreadPool(4);
        List<Future<Integer>> fs=new ArrayList<>();
        for(int i=0;i<4;i++){ final int k=i; fs.add(ex.submit(()->k*k)); }
        List<Integer> res=new ArrayList<>();
        for(Future<Integer> f: fs) res.add(f.get());
        ex.shutdown(); Collections.sort(res);
        System.out.println("CONCURRENCY="+res);
    }
}
