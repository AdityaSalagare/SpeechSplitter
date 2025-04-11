{pkgs}: {
  deps = [
    pkgs.libsndfile
    pkgs.glibcLocales
    pkgs.ffmpeg-full
    pkgs.postgresql
    pkgs.openssl
  ];
}
