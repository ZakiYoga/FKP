function ComingSoon({ title }: { title: string }) {
  return (
    <div className="card card-body text-center py-16 animate-fade-in">
      <p className="text-4xl mb-4">🚧</p>
      <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
      <p className="text-gray-400 text-sm mt-2">Halaman ini sedang dalam pengembangan.</p>
    </div>
  )
}

export default ComingSoon;