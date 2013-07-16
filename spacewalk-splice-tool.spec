# spacewalk-splice-tool package
Name:           spacewalk-splice-tool
Version:        0.29
Release:        1%{?dist}
Summary:        A tool for gathering active system checkin data from spacewalk server and report to Splice server

Group:          Development/Languages
License:        GPLv2+
URL:        https://github.com/splice/spacewalk-splice-tool
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  python2-devel

Requires: python-certutils
Requires: python-oauth2
Requires: splice-common >= 0.77
Requires: /usr/sbin/crond
Requires: katello-cli
Requires: subscription-manager >= 1.8.11

%description
A tool for gathering system checkin data from spacewalk server and report to Splice server

%prep
%setup -q

%build
pushd src
%{__python} setup.py build
popd


%install
rm -rf %{buildroot}
pushd src
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
popd
mkdir -p %{buildroot}/%{_sysconfdir}/sysconfig/
mkdir -p %{buildroot}/%{_sysconfdir}/splice/
mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{_var}/log/%{name}
mkdir -p %{buildroot}/%{_sysconfdir}/cron.d

# Configuration
cp -R etc/splice/* %{buildroot}/%{_sysconfdir}/splice/
cp -R etc/cron.d/* %{buildroot}/%{_sysconfdir}/cron.d/

# Tools
cp bin/* %{buildroot}/%{_bindir}/

# Remove egg info
rm -rf %{buildroot}/%{python_sitelib}/*.egg-info

%clean
rm -rf %{buildroot}

%post
/sbin/service crond condrestart

%postun
/sbin/service crond condrestart

%files
%defattr(-,root,root,-)
%attr(755,root,root) %{_bindir}/spacewalk-splice-checkin
%{python_sitelib}/spacewalk_splice_tool*
%config(noreplace) %{_sysconfdir}/splice/checkin.conf
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/cron.d/spacewalk-sst-sync
%config(noreplace) %attr(644,root,root) %{_sysconfdir}/cron.d/splice-sst-sync
%doc LICENSE

%changelog
* Thu Jul 11 2013 Chris Duryee (beav) <cduryee@redhat.com>
- typoed an argument that broke ssh (cduryee@redhat.com)

* Thu Jul 11 2013 Chris Duryee (beav) <cduryee@redhat.com>
- various fixups (cduryee@redhat.com)

* Tue Jul 02 2013 Chris Duryee (beav) <cduryee@redhat.com>
- remove dep to smmd, which is not always available (cduryee@redhat.com)
- rename rmu to mpu, to avoid confusion (cduryee@redhat.com)
- make SafeConfigParser handle config defaults (cduryee@redhat.com)
- use multithread for enriching RMU (cduryee@redhat.com)
- break queued worker out into something that others can use
  (cduryee@redhat.com)
- checkin.py: support old configs without num_threads option set
  (vitty@redhat.com)

* Fri Jun 28 2013 Chris Duryee (beav) <cduryee@redhat.com>
- multiple small fixups (cduryee@redhat.com)
- updates to checkin.conf (cduryee@redhat.com)
- Test for utils (jslagle@redhat.com)
- Add another test (100% coverage on checkin.py) (jslagle@redhat.com)
- Add basic test for splice_sync (jslagle@redhat.com)
- Do not exit from upload_to_rcs, allow it to be handled by main()
  (jslagle@redhat.com)
- lots of pep8 fixups (cduryee@redhat.com)
- use multiple threads when updating consumers (cduryee@redhat.com)
- fix unit test for org name vs label (cduryee@redhat.com)
- fix sync options unit test (cduryee@redhat.com)

* Fri Jun 21 2013 James Slagle <jslagle@redhat.com> 0.25-1
- 972915 - Change sst to run as splice user in cron file (jslagle@redhat.com)
- Remove unused config option (jslagle@redhat.com)

* Wed Jun 19 2013 Chris Duryee (beav) <cduryee@redhat.com>
- change URL from headpin to sam (cduryee@redhat.com)

* Wed Jun 19 2013 James Slagle <jslagle@redhat.com> 0.23-1
- 972953 - Name roles with the satellite org name instead of org id.  Handle
  org renames as well (jslagle@redhat.com)
- 972942 - Propogate org name changes from satellite to sam
  (jslagle@redhat.com)

* Wed Jun 19 2013 John Matthews <jwmatthews@gmail.com> 0.22-1
- 972969 - No need to specify spacewalk-report command anymore
  (jslagle@redhat.com)
- 973330 - sample-json directory should exist and be writeable
  (jslagle@redhat.com)
- 972879 - Use a seperate lockfile for each sync so they can run at the same
  time.  Also, if neither sync is specified, then run both (added some help
  indicating such) (jslagle@redhat.com)

* Tue Jun 18 2013 James Slagle <jslagle@redhat.com> 0.21-1
- Make sure ssh always connects as root to the satellite (jslagle@redhat.com)

* Tue Jun 11 2013 John Matthews <jwmatthews@gmail.com> 0.20-1
- 972146 - use org ID in role name instead of org name (cduryee@redhat.com)
- 972192 - Handle ssh commands that don't run successfully (jslagle@redhat.com)
- fix typo in cron and shift time over a bit, until we have two lockfiles
  (cduryee@redhat.com)

* Wed Jun 05 2013 Chris Duryee (beav) <cduryee@redhat.com>
- remove katello-checkin file (cduryee@redhat.com)
- data handling fixes (cduryee@redhat.com)

* Wed Jun 05 2013 James Slagle <jslagle@redhat.com> 0.18-1
- rebuild

* Tue Jun 04 2013 James Slagle <jslagle@redhat.com> 0.17-1
- Require katello-cli (jslagle@redhat.com)
- Add releasers.conf (jslagle@redhat.com)

* Tue Jun 04 2013 Chris Duryee (beav) <cduryee@redhat.com>
- utf8 fix and org ordering fix (cduryee@redhat.com)
- re-enable distributor delete, and change report name (cduryee@redhat.com)
- use checkin_date on mpu, not date (cduryee@redhat.com)
- add host/guest mapping report (cduryee@redhat.com)
- use org name instead of label for roles (cduryee@redhat.com)

* Wed May 22 2013 Chris Duryee (beav) <cduryee@redhat.com>
- Revert "use org name instead of org label on roles" (cduryee@redhat.com)

* Wed May 22 2013 Chris Duryee (beav) <cduryee@redhat.com>
- use org name instead of org label on roles (cduryee@redhat.com)
- update virt uuid fact if needed (cduryee@redhat.com)
- host/guest mappings (cduryee@redhat.com)
- send up spacewalk hostname, remove unused fields (cduryee@redhat.com)
- send installed products as part of registration (cduryee@redhat.com)
- use katello org id here, per wes (cduryee@redhat.com)
- fix deletion (cduryee@redhat.com)
- Make http protocol configurable since running katello out of a checkout uses
  http, not https (jslagle@redhat.com)
- Initialize CERT_DIR lazily instead of on import, but still only once
  (jslagle@redhat.com)
- do not create default environment anymore (cduryee@redhat.com)
- fix subscription_status call (cduryee@redhat.com)
- initialize certificatedirectory sooner (cduryee@redhat.com)

* Tue May 14 2013 Chris Duryee (beav) <cduryee@redhat.com>
- use owner key instead of ID when populating MPU (cduryee@redhat.com)
- Set default socket timeout from config file (jslagle@redhat.com)

* Fri May 10 2013 Chris Duryee (beav) <cduryee@redhat.com>
- use new style entitlement_status (cduryee@redhat.com)
- katello->splice changes (cduryee@redhat.com)
- rename most candlepin identifiers to katello (jslagle@redhat.com)
- Make top level url for katello api configurable (jslagle@redhat.com)
- Logging updates (jslagle@redhat.com)
- Better test for spacewalk_sync (jslagle@redhat.com)
- Systems are now keyed by name (jslagle@redhat.com)
- Refactor to not call getRelease on import (jslagle@redhat.com)
- Add test base class (jslagle@redhat.com)
- Set cores per socket fact (jslagle@redhat.com)
- use config options for katello connection, and send up spacewalk hostname
  (cduryee@redhat.com)
- use system name instead of spacewalk ID, and leave OS field blank
  (cduryee@redhat.com)
- use name instead of spacewalk id (cduryee@redhat.com)
- remove some dead code (cduryee@redhat.com)
- Update code to call correct report (jslagle@redhat.com)
- Rename cp-export (jslagle@redhat.com)
- Update synopsis and description of cp-export (jslagle@redhat.com)
- do a checkin and refresh when creating/updating systems (cduryee@redhat.com)
- link distributors when creating new orgs (cduryee@redhat.com)
- Fix config variable reference (jslagle@redhat.com)
- Move ssh options to config file (jslagle@redhat.com)
- Fix channel setting (jslagle@redhat.com)
- Cloned channel report for spacewalk (jslagle@redhat.com)
- Fix clone channel logic for new report (jslagle@redhat.com)
- cloned channel lookup (jslagle@redhat.com)
- Merging upstream master into role change branch (cduryee@redhat.com)
- handle sat admin syncing (cduryee@redhat.com)
- Nothing requires rhic-serve-common anymore (jslagle@redhat.com)
- remove some print statements (cduryee@redhat.com)
- syncing roles (cduryee@redhat.com)
- additional fixes (jslagle@redhat.com)
- Fix config file path (jslagle@redhat.com)
- typo (jslagle@redhat.com)
- Script itself should actually call ssh (jslagle@redhat.com)
- No longer require spacewalk-reports (jslagle@redhat.com)
- Move checkin.conf to just /etc/splice (jslagle@redhat.com)
- Add needed variables to functions (jslagle@redhat.com)
- Run both sync options if neither is specified (jslagle@redhat.com)
- create needed dir (jslagle@redhat.com)
- Fix file location (jslagle@redhat.com)
- Fix file attrs (jslagle@redhat.com)
- spec file updates (jslagle@redhat.com)
- Bash script andcron config for running sst (jslagle@redhat.com)
- refactor into seperate syncs (jslagle@redhat.com)
- remove systems when deleted in sw (cduryee@redhat.com)
- sync org deletes, and unit tests (cduryee@redhat.com)
- import order (jslagle@redhat.com)
- Be sure to always release lockfile (jslagle@redhat.com)
- Add options for seperate sync steps (jslagle@redhat.com)
- whitespace (jslagle@redhat.com)
- Add vim swap files to .gitignore (jslagle@redhat.com)
- lots of changes to support katello (cduryee@redhat.com)
- s/owner/organization in url, no oauth, WIP on owner sync (cduryee@redhat.com)

* Tue Apr 16 2013 John Matthews <jwmatthews@gmail.com> 0.11-1
- Added a CLI option: --sample-json if set to a path we will output the json
  data we send to Splice as separate files (jwmatthews@gmail.com)
- Added rhic-serve-common dep to spec file (jwmatthews@gmail.com)
- default to one socket, instead of blank (cduryee@redhat.com)
- populate org id and name in mpu (cduryee@redhat.com)

* Thu Apr 11 2013 John Matthews <jwmatthews@gmail.com> 0.10-1
- Automatic commit of package [spacewalk-splice-tool] release [0.9-1].
  (jwmatthews@gmail.com)
- Upload Pool/Product/Rules data to splice.common.api during 'checkin' run
  (jwmatthews@gmail.com)
- config cleanup, and removal of some dead code (cduryee@redhat.com)

* Thu Apr 11 2013 John Matthews <jwmatthews@gmail.com> 0.9-1
- Upload Pool/Product/Rules data to splice.common.api during 'checkin' run
  (jwmatthews@gmail.com)
- use oauth instead of username/pass (cduryee@redhat.com)
- spec updates (cduryee@redhat.com)
- delete systems from candlepin that were deleted in spacewalk
  (cduryee@redhat.com)
- do not allow two instances of sst to run at once (cduryee@redhat.com)
- use org ID instead of org name, and clean up logging statements
  (cduryee@redhat.com)
- Read data out of spacewalk DB instead of using APIs (cduryee@redhat.com)
- Use all systems in spacewalk, do not perform group to rhic mapping
  (cduryee@redhat.com)
- add entitlementStatus to MPU (cduryee@redhat.com)
- use qty of the entitlement, not the pool (cduryee@redhat.com)
- send candlepin data to rcs (cduryee@redhat.com)
- set facts in a way that candlepin expects (cduryee@redhat.com)
- candlepin support (cduryee@redhat.com)
- candlepin support (cduryee@redhat.com)

* Fri Feb 01 2013 John Matthews <jwmatthews@gmail.com> 0.8-1
- Change default num sockets to 0 if no data is available
  (jwmatthews@gmail.com)

* Thu Jan 31 2013 John Matthews <jwmatthews@gmail.com> 0.7-1
- Update to handle errors and display error messages from remote server
  (jwmatthews@gmail.com)

* Wed Jan 30 2013 John Matthews <jmatthews@redhat.com> 0.6-1
- Added support for "inactive" systems (jmatthews@redhat.com)
- Update for new location of certs (jmatthews@redhat.com)
- send server metadata before product usage (cduryee@redhat.com)
- find root for cloned channels when calculating product usage
  (cduryee@redhat.com)
- additional debugging, and clone mapping POC (cduryee@redhat.com)
- changes for socket support (wip) (cduryee@redhat.com)
- fixing facts data to match what report server expects (pkilambi@redhat.com)

* Wed Oct 31 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.5-1
- using local config to avoid django interference (pkilambi@redhat.com)

* Wed Oct 31 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.4-1
- requiring current version of splice-common for compatibility
  (pkilambi@redhat.com)

* Wed Oct 31 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.3-1
- Add logging support (pkilambi@redhat.com)
- Adding requires on splice-common (pkilambi@redhat.com)
- updating cron info and added a note if user wants to update the crontab
  (pkilambi@redhat.com)
- adding support to upload product usage (pkilambi@redhat.com)
- adding rel-eng dir (pkilambi@redhat.com)
- updating spec file (pkilambi@redhat.com)

* Mon Oct 29 2012 Pradeep Kilambi <pkilambi@redhat.com> 0.2-1
- new package built with tito

