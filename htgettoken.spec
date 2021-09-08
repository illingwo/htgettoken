%define downloads_version 1.3

Summary: Get OIDC bearer tokens by interacting with Hashicorp vault
Name: htgettoken
Version: 1.3
Release: 1%{?dist}
License: BSD
Group: Applications/System
URL: https://github.com/fermitools/htgettoken
# download with:
# $ curl -o htgettoken-%{version}.tar.gz \
#    https://codeload.github.com/fermitools/htgettoken/tar.gz/%{version}
Source0: %{name}-%{version}.tar.gz
# recreate this with make-downloads
Source1: %{name}-downloads-%{downloads_version}.tar.gz
BuildRequires: python3-pip
BuildRequires: python3-devel
# swig and openssl-devel are needed to prevent an M2Crypto problem with
#   OpenSSL 1.1
BuildRequires: swig
BuildRequires: openssl-devel

%description
htgettoken gets OIDC bearer tokens by interacting with Hashicorp vault

# set nil out debug_package here to avoid stripping
%global debug_package %{nil}

# eliminate .buid-id links on el8, they make python packages clash
%global _build_id_links none

%prep
%setup -q
%setup -q -T -b 1 -n %{name}-downloads-%{downloads_version}

%build
# starts out in htgettoken-downloads

set -e
PYDIR=$PWD/.local
PATH=$PYDIR/bin:$PATH
export PYTHONPATH="`echo $PYDIR/lib*/python*/site-packages|sed 's/ /:/g'`"

# install in reverse order of their download (because dependency downloads
#   come after requested packages)
PKGS="$(tar tf %{SOURCE1} |sed 's,^%{name}-downloads-[^/]*/,,'| grep -v "^\.local"| tac)"
# installing wheel separately first eliminates warnings about falling back
#   to setup.py
WHEELPKG="$(echo "$PKGS"|grep ^wheel)"
PKGS="$(echo "$PKGS"|grep -v ^wheel|paste -sd ' ')"
# --no-build-isolation is needed for offline build of pyinstaller as per
#  https://github.com/pyinstaller/pyinstaller/issues/4557
HOME=$PWD pip3 install --no-cache-dir --no-build-isolation --user $WHEELPKG
HOME=$PWD pip3 install --no-cache-dir --no-build-isolation --user $PKGS

cd ../%{name}-%{version}

PYIOPTS="--noconsole --log-level=WARN"
$PYDIR/bin/pyi-makespec $PYIOPTS --specpath=dist %{name}

# Exclude system libraries from the bundle as documented at
#  https://pyinstaller.readthedocs.io/en/stable/spec-files.html#posix-specific-options
awk '
    {if ($1 == "pyz") print "a.exclude_system_libraries()"}
    {print}
' dist/%{name}.spec >dist/%{name}-lesslibs.spec
$PYDIR/bin/pyinstaller $PYIOPTS --noconfirm --clean dist/%{name}-lesslibs.spec

find dist/%{name} -name '*.*' ! -type d|xargs chmod -x


%install
# starts out in htgettoken-downloads
cd ../%{name}-%{version}

rm -rf $RPM_BUILD_ROOT

mkdir -p $RPM_BUILD_ROOT%{_bindir}
mkdir -p $RPM_BUILD_ROOT%{_datadir}/man/man1
mkdir -p $RPM_BUILD_ROOT%{_libexecdir}/%{name}
cp -r dist/%{name} $RPM_BUILD_ROOT%{_libexecdir}
# somehow through this cp process some files can become non-readable, repair
find $RPM_BUILD_ROOT%{_libexecdir} ! -perm -400|xargs -rt chmod a+r
cat > $RPM_BUILD_ROOT%{_bindir}/%{name} <<'!EOF!'
#!/bin/bash
exec %{_libexecdir}/%{name}/%{name} "$@"
!EOF!
chmod +x $RPM_BUILD_ROOT%{_bindir}/%{name}
gzip -c %{name}.1 >$RPM_BUILD_ROOT%{_datadir}/man/man1/%{name}.1.gz

# extend read and execute permissions to all users
find $RPM_BUILD_ROOT ! -perm -4|xargs -rt chmod a+r
find $RPM_BUILD_ROOT -perm -100 ! -perm -1|xargs -rt chmod a+x

%clean
rm -rf $RPM_BUILD_ROOT

%files
%{_bindir}/%{name}
%{_libexecdir}/%{name}
%{_datadir}/man/man1/%{name}*


%changelog
#- Use the new pyinstaller 4.5 exclude_system_libraries() function instead
#  of the previous hack to exclude system libraries from being bundled.
#- Send the extra 'server' parameter recognized by htvault-config >= 1.5
#  when --secretpath=secret/oauth/creds/%issuer/%credkey:%role, to use
#  shared vault secrets instance (will be default later).

* Tue Jul 13 2021 Dave Dykstra <dwd@fnal.gov> 1.3-1
- Add --kerbprincipal option
- Change the default kerbpath to include issuer and role
- Limit oidc polling to 2 minutes
- Disable oidc authentication when running in the background, that is, when
    none of stdin, stdout, or stderr are on a tty
- Document that audience can be a comma or space separated list
- Updated pip-installed dependent packages to latest versions

* Thu Apr  8 2021 Dave Dykstra <dwd@fnal.gov> 1.2-1
- Fix working with a kerberos domain that is missing from krb5.conf
- Extract more formatted information from http exceptions
- Improve format of printed kerberos exceptions

* Wed Dec 30 2020 Dave Dykstra <dwd@fnal.gov> 1.1-1
- Integrate with htcondor, including these changes:
 - Change --authpath option name to --oidcpath.
 - Add --noidc option.
 - Add --vaulttokenttl option.
 - Make --vaulttokenfile default to /dev/stdout if the ttl is more than
    a million seconds, and also require it to start with /dev/std or
    /dev/fd if the ttl is more than a million seconds.
 - Add --vaulttokeninfile option.
 - Add --nobearertoken option.
 - Add --showbearerurl option.
 - Send progress output to stderr if --vaulttokenfile is /dev/stdout or
     --showbearerurl option is enabled.
- Use a separate version number for the python library downloads tarball.

* Tue Dec 1 2020 Dave Dykstra <dwd@fnal.gov> 1.0-1
- Add --credkey option.
- Add --vaultalias option.
- Add --nokerberos and --kerbpath options.
- Change the name of the --vaultrole option to --role; the short name -r
   remains unchanged.
- Fill out the man page and add a html version of it to the source,
   generated by a Makefile.

* Mon Nov 2 2020 Dave Dykstra <dwd@fnal.gov> 0.5-1
- Set BROWSER variable to prevent xdg-open from running lynx, which hangs.

* Fri Oct 16 2020 Dave Dykstra <dwd@fnal.gov> 0.4-1
- Support the new poll api in addition to the old device_wait api when
  waiting for authorization response
- Use colon as separator in default secret path instead of hyphen
- Add --scopes and --audience options
- Implement the --minsecs option (was present before but didn't work)
- Stop reading old bearer token and remove use of jwt package

* Tue Jul 28 2020 Dave Dykstra <dwd@fnal.gov> 0.3-1
- Avoid including standard system libraries with pyinstaller
- Increase timeout on web browser interaction to 5 minutes
- Set up the interrupt signal to kill the program
- Add BuildRequires for openssl-devel and swig
- Remove confusing code for setting default cafile on RHEL and make setting
   the Debian default more clear

* Wed Jul 22 2020 Dave Dykstra <dwd@fnal.gov> 0.2-1
- Allow for missing xdg-open
- Add some missing "Exception as e" clauses
- Create configdir if missing when needed
- Change from jwt pip package to pyjwt, and disable verify_aud

* Tue Jul 21 2020 Dave Dykstra <dwd@fnal.gov> 0.1-1
- Initial release
