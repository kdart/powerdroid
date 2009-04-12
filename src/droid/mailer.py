#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""Send mails to Power Droids gmail account for testing the sync feature.
Simulates a realistic email conversation so that the Google mail "does
it's thing" in a realistic way.
"""

__author__ = 'dart@google.com (Keith Dart)'

import sys

from pycopia import ezmail
from pycopia import scheduler
from pycopia import sysrandom
from pycopia import words

DEFAULTACCOUNT = "power.android@gmail.com"

DEFAULT_SENDERS = [
  "dart@google.com", "oorm1uw01x@google.com", "mnzjzwsh@google.com",
  "q8rvdcoz4@google.com", "cu7spl@google.com", "wv5wblayf5@google.com",
  "efct3zug4@google.com", "hmetuahi@google.com", "gble1s8@google.com",
  "zxaa3bv7@google.com", "s4tnass72u@google.com", "wutnybr1@google.com",
  "iqzp9hqld6@google.com", "hzk2aixz37@google.com", "oppystu@google.com",
  "f794xsy@google.com", "fhjkjtex8@google.com", "fhiucmz0@google.com",
  "mwq8wxm@google.com", "knb91k@google.com", "t24wv3.fq@google.com",
  "d.2xph@google.com", "lyudyr@google.com", "s3k3.zfzji@google.com",
  "s6ump09fd@google.com", "ug8s31whbs@google.com", "tyb2zt.@google.com",
  "z9fj8qf8@google.com", "wnzp28h5@google.com", "k2p1g0v@google.com",
  "y6.auyyhx@google.com", "gznpvdjlik@google.com", "iwcx4t5i7@google.com",
  "l9t11ga@google.com", "mp6n2s@google.com", "mgoni41@google.com",
  "yvhverr@google.com", "fxots6v1m@google.com", "mdtwqo@google.com",
  "pqbrz5d@google.com", "wdqzac5ain@google.com", "q1e3kbvgqc@google.com",
  "dr84ym@google.com", "cuxqmph@google.com", "b.v.1vl8bl@google.com",
  "ze7aofi@google.com", "mntxwlafep@google.com", "c2cl4d@google.com",
  "i04g1ahbcu@google.com", "jm315p.@google.com", "prjvfv@google.com",
  "a6l8liqe3d@google.com", "ez087cb0i@google.com", "gloqfr5@google.com",
  "zr7zc0zof@google.com", "msnpqpb@google.com", "u.cbb24r@google.com",
  "f0fgjlbd8@google.com", "q6qtuqsg@google.com", "n7y4sg@google.com",
  "kyylfbp@google.com", "hf84fuxn@google.com", "byay0kh@google.com",
  "pq02w.@google.com", "gxu0yxw2t@google.com", "hbt02mc@google.com",
  "iqkvoru@google.com", "q1qavu9yuu@google.com", "y34m9vzo@google.com",
  "i1eraho@google.com", "q13atnh052@google.com", "ewnacqm@google.com",
  "liissv3@google.com", "ecqs5rq4oi@google.com", "tlgqnerjj@google.com",
  "vkk6omkoj@google.com", "e6dd3ouuw3@google.com", "rjvta5@google.com",
  "ksn.1bfs4@google.com", "vr9zis@google.com", "wsq8snqo@google.com",
  "hzu7o9@google.com", "zf5fwrc6mu@google.com", "n3op70@google.com",
  "wcr6q302i.@google.com", "lrl1w9.@google.com", "fve94r6g@google.com",
  "mh36yzx@google.com", "e1qmtwg@google.com", "eu62uf5mt2@google.com",
  "d7cnlmf75@google.com", "q0ykpt@google.com", "g6s0blzrzt@google.com",
  "j7dpu5kpjq@google.com", "y90hmz@google.com", "rbhfolg@google.com",
  "i7uzdm79v@google.com", "dq0w.7@google.com", "te3tyvmd@google.com",
  "ztxrid@google.com", "j8u8fj8@google.com", 
  ]

PARAGRAPHS = [
"""
When in the Course of human events it becomes necessary for one people to
dissolve the political bands which have connected them with another and to
assume among the powers of the earth, the separate and equal station to
which the Laws of Nature and of Nature's God entitle them, a decent
respect to the opinions of mankind requires that they should declare the
causes which impel them to the separation.
""",

"""
We hold these truths to be self-evident, that all men are created equal,
that they are endowed by their Creator with certain unalienable Rights,
that among these are Life, Liberty and the pursuit of Happiness. -- 
That to secure these rights, Governments are instituted among Men,
deriving their just powers from the consent of the governed,  -- That
whenever any Form of Government becomes destructive of these ends, it is
the Right of the People to alter or to abolish it, and to institute new
Government, laying its foundation on such principles and organizing its
powers in such form, as to them shall seem most likely to effect their
Safety and Happiness. Prudence, indeed, will dictate that Governments long
established should not be changed for light and transient causes; and
accordingly all experience hath shewn that mankind are more disposed to
suffer, while evils are sufferable than to right themselves by abolishing
the forms to which they are accustomed. But when a long train of abuses
and usurpations, pursuing invariably the same Object evinces a design to
reduce them under absolute Despotism, it is their right, it is their duty,
to throw off such Government, and to provide new Guards for their future
security.  -- Such has been the patient sufferance of these Colonies;
and such is now the necessity which constrains them to alter their former
Systems of Government. The history of the present King of Great Britain is
a history of repeated injuries and usurpations, all having in direct
object the establishment of an absolute Tyranny over these States. To
prove this, let Facts be submitted to a candid world.
""",

"""
He has refused his Assent to Laws, the most wholesome and necessary for
the public good.
""",

"""
He has forbidden his Governors to pass Laws of immediate and pressing
importance, unless suspended in their operation till his Assent should be
obtained; and when so suspended, he has utterly neglected to attend to
them.
""",

"""
He has refused to pass other Laws for the accommodation of large districts
of people, unless those people would relinquish the right of
Representation in the Legislature, a right inestimable to them and
formidable to tyrants only.
""",

"""
He has called together legislative bodies at places unusual,
uncomfortable, and distant from the depository of their Public Records,
for the sole purpose of fatiguing them into compliance with his measures.
""",

"""
He has dissolved Representative Houses repeatedly, for opposing with manly
firmness his invasions on the rights of the people.
""",

"""
He has refused for a long time, after such dissolutions, to cause others
to be elected, whereby the Legislative Powers, incapable of Annihilation,
have returned to the People at large for their exercise; the State
remaining in the mean time exposed to all the dangers of invasion from
without, and convulsions within.
""",

"""
He has endeavoured to prevent the population of these States; for that
purpose obstructing the Laws for Naturalization of Foreigners; refusing to
pass others to encourage their migrations hither, and raising the
conditions of new Appropriations of Lands.
""",

"""
He has obstructed the Administration of Justice by refusing his Assent to
Laws for establishing Judiciary Powers.
""",

"""
He has made Judges dependent on his Will alone for the tenure of their
offices, and the amount and payment of their salaries.
""",

"""
He has erected a multitude of New Offices, and sent hither swarms of
Officers to harass our people and eat out their substance.
""",

"""
He has kept among us, in times of peace, Standing Armies without the
Consent of our legislatures.
""",

"""
He has affected to render the Military independent of and superior to the
Civil Power.
""",

"""
He has combined with others to subject us to a jurisdiction foreign to our
constitution, and unacknowledged by our laws; giving his Assent to their
Acts of pretended Legislation:
""",

"""
For quartering large bodies of armed troops among us:
""",

"""
For protecting them, by a mock Trial from punishment for any Murders which
they should commit on the Inhabitants of these States:
""",

"""
For cutting off our Trade with all parts of the world:
""",

"""
For imposing Taxes on us without our Consent:
""",

"""
For depriving us in many cases, of the benefit of Trial by Jury:
""",

"""
For transporting us beyond Seas to be tried for pretended offences:
""",

"""
For abolishing the free System of English Laws in a neighbouring Province,
establishing therein an Arbitrary government, and enlarging its Boundaries
so as to render it at once an example and fit instrument for introducing
the same absolute rule into these Colonies
""",

"""
For taking away our Charters, abolishing our most valuable Laws and
altering fundamentally the Forms of our Governments:
""",

"""
For suspending our own Legislatures, and declaring themselves invested
with power to legislate for us in all cases whatsoever.
""",

"""
He has abdicated Government here, by declaring us out of his Protection
and waging War against us.
""",

"""
He has plundered our seas, ravaged our coasts, burnt our towns, and
destroyed the lives of our people.
""",

"""
He is at this time transporting large Armies of foreign Mercenaries to
compleat the works of death, desolation, and tyranny, already begun with
circumstances of Cruelty &amp; Perfidy scarcely paralleled in the most
barbarous ages, and totally unworthy the Head of a civilized nation.
""",

"""
He has constrained our fellow Citizens taken Captive on the high Seas to
bear Arms against their Country, to become the executioners of their
friends and Brethren, or to fall themselves by their Hands.
""",

"""
He has excited domestic insurrections amongst us, and has endeavoured to
bring on the inhabitants of our frontiers, the merciless Indian Savages
whose known rule of warfare, is an undistinguished destruction of all
ages, sexes and conditions.
""",

"""
In every stage of these Oppressions We have Petitioned for Redress in the
most humble terms: Our repeated Petitions have been answered only by
repeated injury. A Prince, whose character is thus marked by every act
which may define a Tyrant, is unfit to be the ruler of a free people.
""",

"""
Nor have We been wanting in attentions to our British brethren. We have
warned them from time to time of attempts by their legislature to extend
an unwarrantable jurisdiction over us. We have reminded them of the
circumstances of our emigration and settlement here. We have appealed to
their native justice and magnanimity, and we have conjured them by the
ties of our common kindred to disavow these usurpations, which would
inevitably interrupt our connections and correspondence. They too have
been deaf to the voice of justice and of consanguinity. We must,
therefore, acquiesce in the necessity, which denounces our Separation, and
hold them, as we hold the rest of mankind, Enemies in War, in Peace
Friends.
""",

"""
We, therefore, the Representatives of the united States of America, in
General Congress, Assembled, appealing to the Supreme Judge of the world
for the rectitude of our intentions, do, in the Name, and by Authority of
the good People of these Colonies, solemnly publish and declare, That
these united Colonies are, and of Right ought to be Free and Independent
States, that they are Absolved from all Allegiance to the British Crown,
and that all political connection between them and the State of Great
Britain, is and ought to be totally dissolved; and that as Free and
Independent States, they have full Power to levy War, conclude Peace,
contract Alliances, establish Commerce, and to do all other Acts and
Things which Independent States may of right do.  
""",

"""
-- And for the support of this Declaration, with a firm reliance on the
protection of Divine Providence, we mutually pledge to each other our
Lives, our Fortunes, and our sacred Honor.
""",
]


def GetFullAddress(name):
    """Return a fully qualified address given a base name.

    Use the configured domain (from ezmail.conf) or the host name if that
    is not available.
    """
    if "@" not in name:
      domain = ezmail.CONFIG.get("domain")
      if domain:
          return "%s@%s" % (name, domain)
      else:
          return "%s@%s" % (name, ezmail._get_hostname())
    else:
      return name


def SendMail(body, from_, subject, To=DEFAULTACCOUNT, headers=None,
      retries=3):
  while retries > 0:
    try:
      return ezmail.ezmail(body, To=To, From=from_, subject=subject, 
          extra_headers=headers)
    except ezmail.MailError: # server might be busy
      scheduler.sleep(1)
      retries -= 1


class MailThread(object):
  """Simulate a group discussion."""
  def __init__(self, number, delay, recipient=DEFAULTACCOUNT, senders=None):
    topic = words.get_random_word()
    question = sysrandom.choice(["Concerning", "A question about", 
        "Tell me about", "What about", "Information regarding",
        "A declaration about", "Help me with"])
    self.subject = "[mail-list] %s %r." % (question, topic)
    self.members = senders or DEFAULT_SENDERS
    self._recipient = recipient
    self._number = int(number)
    self._delay = float(delay)

  def Initiate(self):
    self.initiator = From = sysrandom.choice(self.members)
    body = sysrandom.choice(PARAGRAPHS) + "\n\n-- %s\n" % (From.split("@")[0],)
    self._message_id = SendMail(body, From, self.subject, self._recipient)

  def Respond(self):
    subject = "Re: %s" % (self.subject,)
    from_ = sysrandom.choice(self.members)
    para = sysrandom.choice(PARAGRAPHS)
    body = "Dear %s:\n\n%s\n\n-- %s\n" % (self.initiator.split("@")[0], 
        para, from_.split("@")[0])
    headers = {
      "In-Reply-To": self._message_id, 
      "References": self._message_id,
      }
    SendMail(body, from_, subject, self._recipient, headers)

  def Run(self):
    self.Initiate()
    scheduler.sleep(self._delay)
    for n in range(self._number):
      self.Respond()
      scheduler.sleep(self._delay)


class Mailer(object):
  """Mail a bunch o' messages.
  """

  def __init__(self, topics, messages, delay, recipient, senders=None):
    self._topics = topics
    self._recipient = recipient
    self._senders = map(GetFullAddress, senders or DEFAULT_SENDERS)
    self._messages = messages # messages per topic.
    self._delay = delay

  def Run(self):
    for i in xrange(self._topics):
      mailer = MailThread(self._messages, self._delay, self._recipient,
          self._senders)
      mailer.Run()


def pdmail(argv):
  """pdmail [-h?] [-N <topics>] [-n <messages>] [-d <delay>]
            [-f <fromaddress>,...] [<recipient>]

  Send unique emails to an email account. The Power Droid sync account is
  used by default. Simulates a simple threaded discussion (a question and
  many responses).

  Options:
    -N  <number> Total number of topics to create (default 1).
    -n  <number> Total number of emails to send per topic (default 10).
    -f  <fromaddress>,... comma separated list of source (From) email
        addresses.
    -d  <delay>  Delay, in seconds, between messages (default 60 s).
    -D  Turn on auto debugging.
  """
  import getopt
  recipient = DEFAULTACCOUNT
  senders = None
  Ntopics = 1
  Nmessages = 10
  delay = 60.0
  try:
    opts, args = getopt.getopt(argv[1:], "Dh?d:n:g:N:f:")
  except getopt.GetoptError, err:
    print >>sys.stderr, err
    return 2

  for opt, optarg in opts:
    if opt in ("-h", "-?"):
      print argv[0], ":"
      print pdmail.__doc__
      return 1
    elif opt == "-d":
      delay = float(optarg)
    elif opt == "-n":
      Nmessages = int(optarg)
    elif opt == "-f":
      senders = map(str.strip, optarg.split(","))
    elif opt == "-N":
      Ntopics = int(optarg)
    elif opt == "-D":
      from pycopia import autodebug

  if len(args) > 0:
    recipient = args[0]

  try:
    mailer = Mailer(Ntopics, Nmessages, delay, recipient, senders)
    mailer.Run()
  except KeyboardInterrupt:
    pass

  return 0

