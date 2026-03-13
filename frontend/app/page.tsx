import { SubscribeForm } from "@/components/subscribe-form";

const FEATURED = {
  category: "경제",
  timeAgo: "5분 전",
  title: "실리콘밸리의 다음 물결: AI 인프라에서 에이전트 서비스로의 전환",
  description:
    "단순한 정보 검색을 넘어 실질적인 업무를 수행하는 AI 에이전트가 시장의 중심이 되고 있습니다. 오늘 아침 우리가 주목해야 할 기업과 트렌드를 분석했습니다.",
  image:
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=1200",
};

const ARTICLES = [
  {
    title: "디지털 자산의 미래: 중앙은행 디지털 화폐(CBDC) 보고서",
    description:
      "전 세계 주요 중앙은행들이 현금 없는 사회를 준비하며 발행을 서두르는 CBDC가 가져올 변화를 짚어봅니다.",
    image:
      "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&q=80&w=600",
  },
  {
    title: "하이브리드 워크의 진화, 이제는 '동기화'가 핵심이다",
    description:
      "재택과 출근의 단순 병행을 넘어, 팀원 간의 유기적인 협업을 위한 시스템 구축이 기업의 경쟁력이 되고 있습니다.",
    image:
      "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=600",
  },
  {
    title: "2025 에너지 트렌드: 소형 원자로(SMR)가 대안이 될까?",
    description:
      "탈탄소 시대를 맞이하여 안전성과 효율성을 동시에 잡으려는 SMR 기술의 현주소를 진단합니다.",
    image:
      "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&q=80&w=600",
  },
];

export default function HomePage() {
  return (
    <div className="bg-slate-50 text-slate-900 min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <h1 className="text-2xl font-bold tracking-tighter font-serif text-indigo-700">
              NEWS READER
            </h1>
            <div className="hidden md:flex gap-6 text-sm font-medium text-slate-600">
              {["테크", "비즈니스", "정치", "라이프"].map((cat) => (
                <span key={cat} className="hover:text-indigo-600 cursor-pointer">
                  {cat}
                </span>
              ))}
            </div>
          </div>
          <a
            href="#subscribe"
            className="text-sm font-semibold px-5 py-2 bg-indigo-600 text-white rounded-full shadow-lg shadow-indigo-200 hover:bg-indigo-700 transition"
          >
            구독하기
          </a>
        </div>
      </nav>

      <main className="pt-24 pb-20 max-w-7xl mx-auto px-6">
        {/* Hero */}
        <section className="mb-16">
          <div className="flex items-center gap-2 mb-6 text-indigo-600 font-bold tracking-wider text-xs uppercase">
            <span className="w-2 h-2 bg-indigo-600 rounded-full animate-pulse" />
            실시간 큐레이션
          </div>
          <div className="grid lg:grid-cols-2 gap-10 items-center">
            <div className="overflow-hidden rounded-3xl border border-black/5 shadow-2xl">
              <img
                src={FEATURED.image}
                alt="메인 뉴스"
                className="w-full h-[400px] object-cover hover:scale-105 transition duration-700"
              />
            </div>
            <div>
              <span className="inline-block px-3 py-1 bg-indigo-50 text-indigo-600 text-xs font-bold rounded-md mb-4">
                {FEATURED.category} · {FEATURED.timeAgo}
              </span>
              <h2 className="text-4xl font-bold leading-tight font-serif mb-6">
                &ldquo;{FEATURED.title}&rdquo;
              </h2>
              <p className="text-slate-600 text-lg mb-8 leading-relaxed">
                {FEATURED.description}
              </p>
            </div>
          </div>
        </section>

        {/* Article Cards */}
        <section className="grid md:grid-cols-3 gap-8">
          {ARTICLES.map((article) => (
            <div key={article.title} className="group cursor-pointer">
              <div className="relative overflow-hidden rounded-2xl mb-4 bg-slate-200 aspect-[4/3]">
                <img
                  src={article.image}
                  alt={article.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition duration-500"
                />
              </div>
              <h3 className="text-xl font-bold mb-2 group-hover:text-indigo-600 transition">
                {article.title}
              </h3>
              <p className="text-slate-500 text-sm line-clamp-2">{article.description}</p>
            </div>
          ))}
        </section>

        {/* How It Works */}
        <section className="mt-24 text-center">
          <h2 className="text-2xl font-bold font-serif mb-2">Agent Pipeline</h2>
          <p className="text-slate-500 text-sm mb-10">3단계 멀티 에이전트가 뉴스를 자동으로 수집·요약·큐레이션합니다.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { step: "01", title: "수집", desc: "News Hunter Agent가 멀티 쿼리로 웹을 검색하고 전문을 스크래핑합니다.", icon: "🔍" },
              { step: "02", title: "요약", desc: "Summarizer Agent가 3단계 요약과 핵심 시사점을 추출합니다.", icon: "✍️" },
              { step: "03", title: "큐레이션", desc: "Curator Agent가 점수 기반으로 리드를 선정하고 최종 리포트를 생성합니다.", icon: "📰" },
            ].map(({ step, title, desc, icon }) => (
              <div key={step} className="bg-white rounded-2xl border border-slate-200 p-8 text-left">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{icon}</span>
                  <span className="text-xs font-bold text-indigo-600 tracking-widest">STEP {step}</span>
                </div>
                <h3 className="text-lg font-bold mb-2">{title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA + Subscribe Form */}
        <section id="subscribe" className="mt-24 bg-indigo-900 rounded-[3rem] p-12 text-white relative overflow-hidden shadow-2xl shadow-indigo-200">
          <div className="relative z-10 max-w-xl mx-auto">
            <h2 className="text-3xl font-bold font-serif mb-4 text-center">
              매일 아침, 당신만을 위한 AI 뉴스 브리핑을 받아보세요.
            </h2>
            <p className="text-indigo-200 mb-10 text-center">
              원하는 주제와 발송 시각을 설정하면 매일 이메일로 뉴스를 보내드립니다.
            </p>
            <SubscribeForm variant="dark" />
            <p className="text-xs text-indigo-300 mt-6 text-center">신용카드 없이 무료로 시작하세요.</p>
          </div>
          <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-indigo-800 rounded-full blur-3xl opacity-50" />
          <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-500 rounded-full blur-3xl opacity-30" />
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-8">
          <h2 className="text-xl font-bold font-serif text-indigo-700">NEWS READER</h2>
          <div className="flex gap-8 text-sm text-slate-500">
            <span className="hover:text-indigo-600 cursor-pointer">이용약관</span>
            <span className="hover:text-indigo-600 cursor-pointer">개인정보처리방침</span>
          </div>
          <p className="text-xs text-slate-400">© 2025 News Reader Agent. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
