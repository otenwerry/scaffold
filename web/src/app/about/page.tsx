import Header from "../../components/Header";
import { Card, CardTitle, CardContent } from "@/components/ui/card";

export default function About() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <Card>
          <CardTitle className="text-2xl font-bold text-gray-900 leading-relaxed text-center">About Scaffold</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
            Scaffold only works on Macs with Apple Silicon right now. Compatibility with Intel Macs and Windows machines is coming soon. <br /><br />
            The app looks at your screen only when you finish asking a question, and does not save any of your data.
          </CardContent>
        </Card>
      </main>
    </div>
  );
}