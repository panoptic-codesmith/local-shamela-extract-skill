import java.nio.file.Paths;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.store.FSDirectory;
import org.apache.lucene.document.Document;

public class shamela_probe {
  public static void main(String[] args) throws Exception {
    for (String idx : args) {
      try {
        IndexReader r = DirectoryReader.open(FSDirectory.open(Paths.get(idx)));
        System.out.println("== " + idx + " : docs=" + r.numDocs() + " fields for doc0:");
        Document d = r.document(0);
        d.getFields().forEach(f -> {
          String v = f.stringValue();
          if (v != null && v.length() > 0) {
            String show = v.replace('\n', ' ');
            if (show.length() > 220) show = show.substring(0, 220) + " ... [" + v.length() + " chars]";
            System.out.println("   " + f.name() + ": " + show);
          } else {
            System.out.println("   " + f.name() + ": <" + f.numericValue() + " or binary>");
          }
        });
        r.close();
      } catch (Exception e) {
        System.out.println("== " + idx + " FAILED: " + e);
      }
    }
  }
}
