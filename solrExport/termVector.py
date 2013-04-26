from termDict import TermDictionary


def zipListToDict(tvEntry):
    """
    Because Solr gives us stuff in Json lists in alternating
    key->value pairs, not in a nice dictionary
    >>> zipListToDict([0,'a',1,'b'])
    {0: 'a', 1: 'b'}
    """
    tupled = zip(tvEntry[0::2], tvEntry[1::2])
    return dict(tupled)


class TermVector(object):
    """ A single document's term vector, parsed
        from Solr"""
    @staticmethod
    def __zipTermComponents(definitionField):
        return {key: zipListToDict(value)
                for key, value
                in zipListToDict(definitionField).iteritems()}

    def __init__(self):
        """ Construct tv around a documents tv in the Solr response"""
        super(TermVector, self).__init__()
        self.uniqueKey = None
        self.termVector = {}

    def getFeature(self, feature='tf'):
        return {key: value[feature]
                for key, value in self.termVector.iteritems()}

    def toFeaturePairs(self, termDict):
        return {termDict.termToCol[key]: value for
                key, value in self.termVector.iteritems()}

    def __str__(self):
        return str(self.uniqueKey) + "||" + str(self.termVector)

    @staticmethod
    def fromSolr(tvFromSolr, fieldName):
        tv = TermVector()
        zipped = zipListToDict(tvFromSolr)
        tv.uniqueKey = zipped['uniqueKey']
        tv.termVector = tv.__zipTermComponents(zipped[fieldName])
        return tv

    @staticmethod
    def fromFeaturePairs(termDict, uniqueKey, featurePairs, featureName):
        tv = TermVector()
        tv.uniqueKey = uniqueKey
        tv.termVector = {termDict.colToTerm[col]: {featureName: feature}
                         for col, feature in featurePairs}
        return tv


class TermVectorCollection(object):
    """ A collection of term vectors that represents part of a corpus"""
    def __init__(self, solrResp, fieldName):
        """ Construct a collection of termVectors around the Solr resp"""
        super(TermVectorCollection, self).__init__()
        termVectors = solrResp['termVectors']
        self.termDict = TermDictionary()
        self.tvs = {}
        self.feature = 'tf'  # What feature should we emit for each term
        for tv in termVectors:
            if "uniqueKey" in tv and isinstance(tv, list):
                parsedTv = TermVector.fromSolr(tv, fieldName)
                self.tvs[parsedTv.uniqueKey] = parsedTv
                self.termDict.addTerms(parsedTv.termVector.keys())

    def merge(self, tvc):
        """ Merge tvc into self """
        self.tvs = dict(tvc.tvs.items() + self.tvs.items())
        self.termDict.appendTd(tvc.termDict)

    def setFeature(self, feature):
        validSolrFeatures = ('tf-idf', 'tf', 'df')
        if feature in validSolrFeatures:
            self.feature = feature
        else:
            raise ValueError("Solr only exports tf, tf-idf, or df; "
                             "you requested %s" %
                             feature)

    def __str__(self):
        return "Term Vectors %i; Terms %i" % (len(self.tvs),
                                              self.termDict.numTerms())

    def __iter__(self):
        """ Generate feature pairs"""
        for key, tv in self.tvs.iteritems():
            yield {col: value[self.feature] for col, value
                   in tv.toFeaturePairs(self.termDict).iteritems()}.items()

    def toCsc(self):
        """ Get all in csc form"""
        from gensim import matutils
        return matutils.corpus2csc(self)

    def keyIter(self):
        """ Return an iterator that iterates the names of
            documents in parallel with the feature pairs"""
        return iter(self.tvs.keys())


if __name__ == "__main__":
    import doctest
    doctest.testmod()
