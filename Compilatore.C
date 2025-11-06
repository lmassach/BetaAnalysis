//{
#include "TAxis.h"
#include "TCanvas.h"
#include "TFile.h"
#include "TH1.h"
#include "TH1D.h"
#include "TMath.h"
#include "TStopwatch.h"
#include "include/Chameleon.h"
#include "include/ConfigFile.hpp"
#include "include/general.hpp"
#include "src/Analyzer.hpp"
#include <Riostream.h>
#include <TBranch.h>
#include <TList.h>
#include <TObject.h>
#include <TROOT.h>
#include <TSystem.h>
#include <TSystemDirectory.h>
#include <TSystemFile.h>
#include <TTree.h>

void Compilatore() {

  gSystem->CompileMacro("src/general.cpp", "kg");
  gSystem->CompileMacro("src/Chameleon.cpp", "kg");
  gSystem->CompileMacro("src/ConfigFile.cpp", "kg");
  gSystem->CompileMacro("src/Analyzer.cpp", "kg");
  gSystem->CompileMacro("analisi.C", "kg");

  gROOT->ProcessLine("analisi()");
}
