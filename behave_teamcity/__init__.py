from behave.formatter.base import Formatter
from behave.model_describe import ModelDescriptor
from teamcity import messages
from teamcity.messages import TeamcityServiceMessages

class BehaveTeamCityServiceMessages(TeamcityServiceMessages):
    def message(self, messageName, **properties):
        timestamp = self.now().strftime("%Y-%m-%dT%H:%M:%S.") + "%03d" % (self.now().microsecond / 1000)
        message = ("##teamcity[%s timestamp='%s'" % (messageName, timestamp))

        for k in sorted(properties.keys()):
            value = properties[k]
            if value is None:
                continue

            message += (" %s='%s'" % (k, self.escapeValue(value)))

        if self.encoding and isinstance(message, text_type):
            message = message.encode(self.encoding)

        # Python may buffer it for a long time, flushing helps to see real-time result
        self.output.write(message)
        self.output.flush()


class TeamcityFormatter(Formatter):
    description = "Test"

    def __init__(self, stream_opener, config):
        super(TeamcityFormatter, self).__init__(stream_opener, config)
        self.current_feature = None
        self.current_scenario = None
        self.current_step = None
        self.msg = messages.TeamcityServiceMessages()

    def feature(self, feature):
        self.current_feature = feature
        self.current_scenario = None
        self.current_step = None
        self.msg.testSuiteStarted(self.current_feature.name)

    def scenario(self, scenario):
        self.step_messages = ''
        if self.current_scenario and self.current_scenario.status == "skipped":
            self.msg.testIgnored(self.current_scenario.name)

        self.current_scenario = scenario
        self.current_step = None
        self.msg.testStarted(self.current_scenario.name, captureStandardOutput='true')


    def result(self, step_result):

        self.current_step = step_result
        if self.current_step.status == "passed":
            self.step_messages += ('-> done: ' + self.current_step.name + '  (' + str(round(self.current_step.duration, 1)) + 's)\n')
        if self.current_scenario.status == "untested":
            return

        if self.current_scenario.status == "passed":
            self.msg.message('testStdErr', name=self.current_scenario.name, out=self.step_messages[:-1])
            self.step_messages = ''
            self.msg.message('testFinished', name=self.current_scenario.name,
                             duration=str(self.current_scenario.duration), flowId=None)

        if self.current_scenario.status == "failed":
            self.msg.message('testStdErr', name=self.current_scenario.name, out=self.step_messages[:-1])
            self.step_messages = ''
            name = self.current_step.name

            error_msg = "Step failed: {}".format(name)
            if self.current_step.table:
                table = ModelDescriptor.describe_table(self.current_step.table, None)
                error_msg = "{}\nTable:\n{}".format(error_msg, table)

            if self.current_step.text:
                text = ModelDescriptor.describe_docstring(self.current_step.text, None)
                error_msg = "{}\nText:\n{}".format(error_msg, text)

            error_details = step_result.error_message

            self.msg.testFailed(self.current_scenario.name, message=error_msg, details=error_details)
            self.msg.message('testFinished', name=self.current_scenario.name,
                             duration=str(self.current_scenario.duration), flowId=None)

    def eof(self):
        self.msg.testSuiteFinished(self.current_feature.name)
