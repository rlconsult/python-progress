import progressbar


class CrazyFileTransferSpeed(progressbar.FileTransferSpeed):
    "It's bigger between 45 and 80 percent"

    def update(self, pbar):
        if 45 < pbar.percentage() < 80:
            return 'Bigger Now ' + progressbar.FileTransferSpeed.update(self,
                                                                        pbar)
        else:
            return progressbar.FileTransferSpeed.update(self, pbar)


def test_crazy_file_transfer_speed_widget():
    widgets = [
        # CrazyFileTransferSpeed(),
        ' <<<',
        progressbar.Bar(),
        '>>> ',
        progressbar.Percentage(),
        ' ',
        progressbar.ETA(),
    ]

    p = progressbar.ProgressBar(widgets=widgets, max_value=1000)
    # maybe do something
    p.start()
    for i in range(0, 200, 5):
        # do something
        p.update(i + 1)
    p.finish()
